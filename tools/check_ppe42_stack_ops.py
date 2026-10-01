#!/usr/bin/env python3
"""Check that the PPE42 stack test app uses the stack instructions."""

from __future__ import annotations

import re
import sys
from pathlib import Path

FUNCTION = re.compile(r"^[0-9a-fA-F]+ <([^>]+)>:")
INSTRUCTION = re.compile(r"^\s*[0-9a-fA-F]+:\s+(?:[0-9a-fA-F]{2}\s+){4}(\S+)\s*(.*)$")
STACK_OPERAND = re.compile(r"^r1,\s*([+-]?\d+)\(r1\)$")


def main(path: Path) -> int:
    in_outer = False
    instructions: list[tuple[str, str]] = []
    for line in path.read_text().splitlines():
        if match := FUNCTION.match(line):
            if in_outer:
                break
            in_outer = match.group(1) == "ppe42_stack_outer"
        elif in_outer and (match := INSTRUCTION.match(line)):
            instructions.append((match.group(1), match.group(2).strip()))

    if not instructions:
        print(f"{path}: ppe42_stack_outer was not found", file=sys.stderr)
        return 1

    saves = [(index, operands) for index, (name, operands) in enumerate(instructions)
             if name == "stsku"]
    restores = [(index, operands) for index, (name, operands) in enumerate(instructions)
                if name == "lsku"]
    if len(saves) != 1 or len(restores) != 1:
        print(f"{path}: expected one stsku and one lsku in ppe42_stack_outer; "
              f"found {len(saves)} and {len(restores)}", file=sys.stderr)
        return 1

    save_index, save_operands = saves[0]
    restore_index, restore_operands = restores[0]
    save = STACK_OPERAND.fullmatch(save_operands)
    restore = STACK_OPERAND.fullmatch(restore_operands)
    names = [name for name, _ in instructions]
    calls = [index for index, name in enumerate(names) if name == "bl"]
    if (not save or not restore or not calls or
            not save_index < calls[0] < restore_index or
            "blr" not in names[restore_index + 1:] or
            int(save.group(1)) >= 0 or int(restore.group(1)) != -int(save.group(1)) or
            int(restore.group(1)) < 16 or int(restore.group(1)) % 8 != 0 or
            int(restore.group(1)) > 32760 or
            any(name in {"mflr", "mtlr", "stwu"} for name in names)):
        print(f"{path}: invalid stsku/lsku prologue and epilogue in "
              "ppe42_stack_outer", file=sys.stderr)
        return 1

    print(f"ppe42_stack_outer: stsku {save_operands}; lsku {restore_operands}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
