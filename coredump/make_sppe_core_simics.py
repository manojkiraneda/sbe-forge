#!/usr/bin/env python3
"""Capture Odyssey SPPE PIBMEM and PK threads as one LLDB ELF core.

Arguments: optional matching firmware ELF or .syms file, then workspace directory.
Alternatively pass --current-thread and --priority-map to recover PK threads
without a symbol file. These are symbol addresses, not the values stored there.
The Simics command uses current_thread and priority_map for these addresses.
Omit the ELF to capture memory and live CPU registers without PK thread recovery.
From a stopped Simics prompt:
    run-python-file /path/to/make_sppe_core_simics.py
    make-sppe-core workspace = "/path/to/workspace" current_thread = 0xfffcec48 priority_map = 0xfffcec70
    make-sppe-core workspace = "/path/to/workspace" elf = "/path/to/firmware.out"

run-python-file accepts only a filename; it does not pass Python arguments.

When launched with Python inside a Simics environment:
    python3 make_sppe_core_simics.py /path/to/workspace
    python3 make_sppe_core_simics.py /path/to/odyssey_sppe.out /path/to/workspace

The matching ELF supplies PK global addresses and the ELF entry point.
DWARF is not needed to create the core, but LLDB uses it for source lines and
local variables.
Set SPPE_PC_SOURCE=iar if stopped at the faulting instruction, or set
SPPE_FAULT_R1 to override automatic recovery of the interrupted stack.
"""

import argparse
import ast
import json
import os
from pathlib import Path
import re
import struct
import sys

import simics
from sim_commands import quiet_run_command


MEMORY_OBJECT = os.environ.get(
    "SPPE_MEMORY_OBJECT", "sled0.loggerhead.dimm0.odyssey.sppe_mibo")
REGISTER_COMMAND = os.environ.get("SPPE_REGISTER_COMMAND", "sregs-poz ody:p0")
MEM_START = 0xFFF80000
MEM_SIZE = 0x80000
PK_THREADS = 32
PC_SOURCE = os.environ.get("SPPE_PC_SOURCE", "srr0")


def capture_registers(raw_regs_file):
    result = quiet_run_command(REGISTER_COMMAND)
    output = result[1] if isinstance(result, tuple) else result
    if not isinstance(output, str):
        output = str(output)
    raw_regs_file.write_text(output)
    match = re.search(r"pregs:.*?(\[\[.*\]\])", output, re.DOTALL)
    if match:
        pairs = ast.literal_eval(match.group(1))
        registers = {str(name).lower(): int(value) & 0xFFFFFFFF
                     for name, value in pairs if not str(name).startswith("d")}
    else:
        pairs = re.findall(r"\|\s*([A-Za-z][A-Za-z0-9]*)\s*\|\s*"
                           r"(0[xX][0-9a-fA-F]+)\s*\|", output)
        registers = {name.lower(): int(value, 16)
                     for name, value in pairs if not name.lower().startswith("d")}
    if "r1" not in registers or PC_SOURCE not in registers:
        raise RuntimeError("Could not find r1 and {} in {}; inspect {}"
                           .format(PC_SOURCE, REGISTER_COMMAND, raw_regs_file))
    return registers


def word(memory, address):
    offset = address - MEM_START
    if offset < 0 or offset + 4 > len(memory):
        raise ValueError("Address outside PIBMEM: 0x{:08x}".format(address))
    return struct.unpack_from(">I", memory, offset)[0]


def elf_details(path):
    """Read AT_ENTRY and PK symbols from ELF headers and .symtab, not DWARF."""
    elf = path.read_bytes()
    if (len(elf) < 52 or elf[:7] != b"\x7fELF\x01\x02\x01" or
            struct.unpack_from(">H", elf, 18)[0] != 20):
        raise ValueError("Expected a 32-bit big-endian PowerPC ELF")
    entry = struct.unpack_from(">I", elf, 24)[0]
    section_offset = struct.unpack_from(">I", elf, 32)[0]
    section_size, section_count = struct.unpack_from(">HH", elf, 46)
    sections = [struct.unpack_from(">10I", elf, section_offset + i * section_size)
                for i in range(section_count)]
    wanted = {"__pk_current_thread", "__pk_priority_map"}
    found = {}
    for section in sections:
        if section[1] != 2 or not section[9]:  # SHT_SYMTAB
            continue
        strings = sections[section[6]]
        names = elf[strings[4]:strings[4] + strings[5]]
        for offset in range(section[4], section[4] + section[5], section[9]):
            name_offset, value = struct.unpack_from(">II", elf, offset)
            if name_offset >= len(names):
                continue
            end = names.find(b"\0", name_offset)
            name = names[name_offset:end].decode("ascii", "replace")
            if name in wanted:
                found[name] = value
    missing = wanted - found.keys()
    if missing:
        raise ValueError("ELF lacks PK symbols {}; use the matching linked ELF"
                         .format(", ".join(sorted(missing))))
    return entry, found


def symbol_details(path):
    """Read PK addresses from an nm-style .syms file; no AT_ENTRY is needed."""
    wanted = {"__pk_current_thread", "__pk_priority_map"}
    found = {}
    for line in path.read_text().splitlines():
        match = re.fullmatch(
            r"\s*([0-9a-fA-F]+)\s+(?:[0-9a-fA-F]+\s+)?[A-Za-z?]\s+(\S+)\s*",
            line)
        if match and match.group(2) in wanted:
            found[match.group(2)] = int(match.group(1), 16)
    missing = wanted - found.keys()
    if missing:
        raise ValueError("Symbol file lacks PK symbols: {}".format(
            ", ".join(sorted(missing))))
    return None, found


def restore_fault_lr(memory, registers):
    """The exception FFDC holds the LR before the handler changed it."""
    if PC_SOURCE != "srr0" or "sprg0" not in registers:
        return
    address = registers["sprg0"]
    if not MEM_START <= address <= MEM_START + len(memory) - 20:
        return
    magic, saved_pc, saved_lr = (word(memory, address + field)
                                 for field in (0, 4, 16))
    if (magic & 0xFFFF) == 0xA501 and saved_pc == registers["srr0"]:
        registers["lr"] = saved_lr
        print("Restored fault-time LR: 0x{:08x}".format(saved_lr))


def fault_stack_pointer(memory, live_sp, limit, stack_base):
    """Find the interrupted backchain above the exception handler frame."""
    start = (max(live_sp, limit) + 7) & ~7
    for candidate in range(start, stack_base, 8):
        cursor = candidate
        links = 0
        code_returns = 0
        while links < 8:
            parent = word(memory, cursor)
            if (parent <= cursor or parent > stack_base or parent & 7 or
                    parent - cursor > 4096):
                break
            if MEM_START <= word(memory, parent + 4) < MEM_START + len(memory):
                code_returns += 1
            cursor = parent
            links += 1
        if links >= 3 and code_returns:
            return candidate
    raise ValueError("Could not recover fault-time r1; set SPPE_FAULT_R1")


def make_note(kind, data):
    name = b"CORE\0"
    return (struct.pack(">III", len(name), len(data), kind)
            + name.ljust((len(name) + 3) & ~3, b"\0")
            + data.ljust((len(data) + 3) & ~3, b"\0"))


def thread_note(registers, pc, thread_id):
    # Linux/PPC32 elf_gregset_t: r0-r31, nip, msr, orig_r3, ctr, link,
    # xer, ccr, mq, trap, dar, dsisr, result.
    values = [registers.get("r{}".format(i), 0) for i in range(32)]
    values += [pc, registers.get("msr", 0), 0, registers.get("ctr", 0),
               registers.get("lr", 0), registers.get("xer", 0),
               registers.get("cr", 0), 0, 0, 0, 0, 0]
    status = bytearray(72)
    struct.pack_into(">I", status, 24, thread_id)
    status += struct.pack(">44I", *values)
    return make_note(1, status)  # NT_PRSTATUS


def saved_thread_registers(memory, saved_sp):
    # PkThreadContext in ppe42_context.h: saved by the PK context switch.
    offsets = {"r0": 0x10, "r3": 0x18, "r4": 0x1c, "r5": 0x20,
               "r6": 0x24, "r7": 0x28, "r8": 0x2c, "r9": 0x30,
               "r10": 0x34, "xer": 0x38, "ctr": 0x3c, "pc": 0x40,
               "msr": 0x44, "r28": 0x48, "r29": 0x4c, "r30": 0x50,
               "r31": 0x54, "cr": 0x08, "lr": 0x5c}
    registers = {name: word(memory, saved_sp + offset)
                 for name, offset in offsets.items()}
    registers["r1"] = word(memory, saved_sp)  # pre-save SP/backchain
    return registers


def make_core(memory, registers, entry=None, symbols=None, fault_r1=None):
    current = word(memory, symbols["__pk_current_thread"]) if symbols else 0
    threads = ([(priority, word(memory, symbols["__pk_priority_map"] + 4 * priority))
                for priority in range(PK_THREADS)] if symbols else [])
    threads = [(priority, tcb) for priority, tcb in threads if tcb]

    if current and PC_SOURCE == "srr0":
        if fault_r1 is None:
            fault_r1 = fault_stack_pointer(
                memory, registers["r1"], word(memory, current + 4),
                word(memory, current + 8))
    if fault_r1 is not None:
        registers["r1"] = fault_r1

    current_priority = next((priority for priority, tcb in threads
                             if tcb == current), PK_THREADS)
    notes = thread_note(registers, registers[PC_SOURCE], current_priority)
    for priority, tcb in threads:
        if tcb != current:
            saved = saved_thread_registers(memory, word(memory, tcb))
            notes += thread_note(saved, saved["pc"], priority)
    # AT_ENTRY lets LLDB load the firmware's sections at linked addresses.
    if entry is not None:
        notes += make_note(6, struct.pack(">IIII", 9, entry, 0, 0))

    note_offset = 52 + 2 * 32
    memory_offset = note_offset + len(notes)
    ident = b"\x7fELF" + bytes([1, 2, 1, 3]) + bytes(8)
    header = struct.pack(">16sHHIIIIIHHHHHH", ident, 4, 20, 1,
                         registers[PC_SOURCE], 52, 0, 0, 52, 32, 2,
                         0, 0, 0)
    note_header = struct.pack(">IIIIIIII", 4, note_offset, 0, 0,
                              len(notes), len(notes), 0, 4)
    load_header = struct.pack(">IIIIIIII", 1, memory_offset, MEM_START, 0,
                              len(memory), len(memory), 7, 1)
    return header + note_header + load_header + notes + memory, threads, fault_r1


def pk_symbol_addresses(current_thread, priority_map):
    if (current_thread is None) != (priority_map is None):
        raise ValueError("Supply both current_thread and priority_map addresses")
    if current_thread is None:
        return None
    symbols = {}
    for name, value, size in (("__pk_current_thread", current_thread, 4),
                              ("__pk_priority_map", priority_map, 4 * PK_THREADS)):
        address = int(value, 0) if isinstance(value, str) else value
        if address % 4 or not MEM_START <= address <= MEM_START + MEM_SIZE - size:
            raise ValueError("{} must be a word-aligned address within PIBMEM".format(name))
        symbols[name] = address
    return symbols


def main(elf_file=None, workspace=".", current_thread=None, priority_map=None):
    elf_file = Path(elf_file).expanduser().resolve() if elf_file else None
    workspace = Path(workspace).expanduser().resolve()
    pibmem_file = workspace / "sppe_pibmem.bin"
    regs_file = workspace / "sppe_registers.txt"
    raw_regs_file = workspace / "sppe_registers_raw.txt"
    core_file = workspace / "sppe.core"
    if PC_SOURCE not in ("iar", "srr0"):
        raise ValueError("SPPE_PC_SOURCE must be iar or srr0")
    entry = None
    symbols = pk_symbol_addresses(current_thread, priority_map)
    if symbols is not None and elf_file is not None:
        raise ValueError("Supply PK addresses or a symbol file, not both")
    if symbols is not None:
        print("Using explicit PK symbol addresses: {}".format(
            ", ".join("{}=0x{:08x}".format(name, value)
                      for name, value in sorted(symbols.items()))))
    elif elf_file is not None:
        if not elf_file.is_file():
            raise RuntimeError("Firmware ELF or symbol file not found: {}".format(elf_file))
        if elf_file.suffix == ".syms":
            entry, symbols = symbol_details(elf_file)
        else:
            entry, symbols = elf_details(elf_file)
        print("Using matching firmware symbols: {}".format(elf_file))
    else:
        print("No ELF: capturing live CPU registers and PIBMEM; "
              "PK threads and automatic fault-stack recovery are unavailable.")

    workspace.mkdir(parents=True, exist_ok=True)

    # Stop Simics before invoking this script: memory and registers must
    # describe the same instant.
    simics.SIM_run_command(
        "{}.save-file filename = {} start = 0x{:X} length = 0x{:X} -overwrite"
        .format(MEMORY_OBJECT, json.dumps(str(pibmem_file)),
                MEM_START, MEM_SIZE))
    memory = pibmem_file.read_bytes()
    if len(memory) != MEM_SIZE:
        raise RuntimeError("Expected 0x{:X} PIBMEM bytes, got 0x{:X}"
                           .format(MEM_SIZE, len(memory)))
    registers = capture_registers(raw_regs_file)
    restore_fault_lr(memory, registers)
    regs_file.write_text("".join("{}=0x{:08x}\n".format(name, value)
                                 for name, value in registers.items()))

    override = os.environ.get("SPPE_FAULT_R1")
    fault_r1 = int(override, 0) if override else None
    core, threads, fault_r1 = make_core(
        memory, registers, entry, symbols, fault_r1)
    core_file.write_bytes(core)
    print("PK priorities: {}".format(
        ", ".join(str(priority) for priority, _ in threads)))
    if fault_r1 is not None:
        print("Fault-time r1: 0x{:08x}".format(fault_r1))
    executable = ("{} ".format(elf_file)
                  if elf_file and elf_file.suffix != ".syms" else "")
    print("Created {}. Open with: lldb {}-c {}".format(
        core_file, executable, core_file))


def register_simics_command():
    from cli import arg, new_command, str_t, int_t

    def capture(workspace, elf, current_thread, priority_map):
        main(elf_file=elf, workspace=workspace,
             current_thread=current_thread, priority_map=priority_map)

    new_command(
        "make-sppe-core", capture,
        args=[arg(str_t, "workspace"), arg(str_t, "elf", "?", None),
              arg(int_t, "current_thread", "?", None),
              arg(int_t, "priority_map", "?", None)],
        short="Capture SPPE memory and registers as an ELF core",
        doc="Capture PIBMEM and CPU registers into the workspace directory. "
            "Supply current_thread and priority_map symbol addresses, or a matching "
            "firmware ELF or .syms file, to recover PK threads.")
    print('Loaded: make-sppe-core workspace = "/path/to/workspace" '
          '[elf = "/path/to/firmware.out"]')


if __name__ == "__main__" and Path(sys.argv[0]).name == "make_sppe_core_simics.py":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", nargs="?", help="Optional matching firmware ELF or .syms path")
    parser.add_argument("workspace", help="Directory for core and capture files")
    parser.add_argument("--current-thread", type=lambda value: int(value, 0),
                        help="Address of __pk_current_thread (hex or decimal)")
    parser.add_argument("--priority-map", type=lambda value: int(value, 0),
                        help="Address of __pk_priority_map (hex or decimal)")
    args = parser.parse_args()
    main(args.elf, args.workspace, args.current_thread, args.priority_map)
elif __name__ == "__main__":
    # SIM_source_python runs in Simics' main namespace with its launcher argv.
    # Never feed those arguments to argparse (SystemExit can terminate Simics).
    register_simics_command()
