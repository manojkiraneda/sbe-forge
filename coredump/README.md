# Odyssey SPPE core dumps from Simics

`make_sppe_core_simics.py` captures Odyssey SPPE PIBMEM and registers as a
32-bit big-endian PowerPC ELF core for LLDB. With PK symbol addresses, it also
captures saved PK thread contexts. No firmware ELF is required during capture.

## Capture a core

Stop Simics before capture so memory and registers describe the same instant.
The Odyssey debug framework must be loaded and `sregs-poz ody:p0` must return
registers for the intended SPPE.

Load the script once in the Simics session, using your checkout's absolute path:

```text
simics> run-python-file /path/to/sbe-forge/coredump/make_sppe_core_simics.py
```

Then supply an output directory and the addresses of `__pk_current_thread` and
`__pk_priority_map` from the running firmware's matching `.syms` file:

```text
simics> make-sppe-core workspace = "/path/to/sppe-core" current_thread = 0xfffcec38 priority_map = 0xfffcec60
```

These example addresses are build-specific. Look up yours with:

```sh
rg '__pk_current_thread|__pk_priority_map' /path/to/odyssey_sppe.syms
```

Use the first hexadecimal column as the address. Pass the symbol addresses,
not the pointer values stored at those addresses. Both must be supplied together.
Addresses can move after a firmware rebuild.

Alternatively, let the script read the addresses from a matching symbol file:

```text
simics> make-sppe-core workspace = "/path/to/sppe-core" elf = "/path/to/odyssey_sppe.syms"
```

The `elf` argument also accepts the matching `odyssey_sppe.out` ELF. Do not
combine a symbol file with explicit addresses.

For just PIBMEM and live CPU registers, omit the addresses and symbol file:

```text
simics> make-sppe-core workspace = "/path/to/sppe-core"
```

This mode cannot enumerate PK threads or automatically recover the interrupted
stack pointer. `run-python-file` takes only a filename; pass capture arguments
to `make-sppe-core`, not to `run-python-file`.

The output directory is created if needed. Each capture overwrites:

| File | Contents |
| --- | --- |
| `sppe.core` | ELF core with register notes and PIBMEM |
| `sppe_pibmem.bin` | Raw 512 KiB PIBMEM at `0xfff80000` |
| `sppe_registers_raw.txt` | Original debug-framework register output |
| `sppe_registers.txt` | Parsed registers before stack-pointer recovery |

## Inspect with LLDB

Open the core alone to inspect its captured registers and memory:

```sh
lldb -c /path/to/sppe-core/sppe.core
```

For function names, source lines, local variables, and firmware unwind
information, load the matching unstripped `.out` file:

```sh
lldb /path/to/odyssey_sppe.out -c /path/to/sppe-core/sppe.core
```

When capture used explicit addresses or `.syms`, explicitly map the firmware
at its linked addresses:

```text
(lldb) target modules load --file odyssey_sppe.out --slide 0
(lldb) thread list
(lldb) bt all
(lldb) register read
```

If the core is already open without an executable, add it first:

```text
(lldb) target modules add /path/to/odyssey_sppe.out
(lldb) target modules load --file odyssey_sppe.out --slide 0
(lldb) bt all
```

A `.syms` file supplies addresses for capture; it does not supply LLDB with DWARF
or unwind information. Recovered PK threads can have identical PCs when they
are suspended in the same scheduler routine. Some contexts may still have only
one frame, depending on their stack state and available unwind information.

## Capture settings

Set these environment variables in Simics' Python environment **before loading
the script**. For example:

```text
simics> @import os
simics> @os.environ["SPPE_PC_SOURCE"] = "iar"
simics> run-python-file /path/to/sbe-forge/coredump/make_sppe_core_simics.py
```

| Variable | Default | Purpose |
| --- | --- | --- |
| `SPPE_MEMORY_OBJECT` | `sled0.loggerhead.dimm0.odyssey.sppe_mibo` | PIBMEM object to save |
| `SPPE_REGISTER_COMMAND` | `sregs-poz ody:p0` | Register command for the selected SPPE |
| `SPPE_PC_SOURCE` | `srr0` | Use the saved exception PC; choose `iar` for the live instruction PC |
| `SPPE_FAULT_R1` | unset | Explicit interrupted stack pointer, parsed as hex or decimal |

`SPPE_FAULT_R1` is read on each capture. With PK addresses and `srr0`, the script
attempts interrupted-stack recovery automatically. Without PK addresses, it
retains the live stack pointer unless an override is supplied.

If LLDB shows PC zero, inspect the raw register output: check both `iar` and
`srr0`, confirm the selected SPPE has started, and confirm the PC source suits
the stopped state. The dump includes only PIBMEM; addresses outside that range
cannot be read from this core.
