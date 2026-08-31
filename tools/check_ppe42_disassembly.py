#!/usr/bin/env python3
"""Strictly validate llvm-objdump output against the PPE42 ISA."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

INSTRUCTION_ROW = re.compile(
    r"^\s*[0-9a-fA-F]+:\s+(?P<bytes>(?:(?:[0-9a-fA-F]{2})\s+){4})"
    r"(?P<mnemonic>[A-Za-z][A-Za-z0-9_.+-]*)\b"
)
def mnemonic_set(values: str) -> set[str]:
    return set(values.split())


# Reviewed against PPE42_ISA.md and the PPE42/PPE42X/PPE42XM User's Manual.
# These are llvm-objdump spellings, so aliases and record forms are explicit.
PPE42_ALLOWLIST = mnemonic_set("""
add add. addc addc. addco addco. adde adde. addeo addeo.
addi addic addic. addis addme addme. addmeo addmeo. addze addze. addzeo addzeo.
and and. andc andc. andi. andis. cntlzw cntlzw.
eqv eqv. extsb extsb. extsh extsh. nand nand. neg neg. nego nego.
nor nor. or or. orc orc. ori oris xor xor. xori xoris
rlwimi rlwimi. rlwinm rlwinm. rlwnm rlwnm. slw slw. sraw sraw. srawi srawi. srw srw.
sub sub. subc subc. subf subf. subfc subfc. subfco subfco.
subfe subfe. subfeo subfeo. subfic subfme subfme. subfmeo subfmeo.
subfze subfze. subfzeo subfzeo. mullhw mullhw. mullhwu mullhwu.
cmpw cmpwi cmplw cmplwi
b ba bl bla bc bca bcl bcla bcctr bcctrl bclr bclrl
bdnz bdnza bdnzl bdnzla bdnzlr bdnzlrl bdz bdza bdzl bdzla bdzlr bdzlrl
bf bfa bfctr bfctrl bfl bfla bflr bflrl
bt bta btctr btctrl btl btla btlr btlrl
bctr bctrl blr blrl
lbz lbzu lbzux lbzx lha lhau lhaux lhax lhz lhzu lhzux lhzx
lwbrx lwarx lwz lwzu lwzux lwzx
stb stbu stbux stbx sth sthbrx sthu sthux sthx stw stwbrx stwcx. stwu stwux stwx
lvd lvdu lvdx stvd stvdu stvdx lsku stsku
mfcr mfmsr mfspr mftb mftbl mftbu mflr mfctr mfxer
mtcr0 mtcrf mtmsr mtspr mtlr mtctr mtxer rfi sync
dcbf dcbi dcbq dcbt dcbz
nop li lis mr not clrlwi clrrwi rotlwi rotrwi slwi srwi
bng bnl bne bso bns bun bnbw bnbwl bnbwi bnbwil
clrbw. clrbwi. clrbwbc clrbwbcl clrbwibc clrbwibcl
clrbwbz clrbwbzl clrbwbnz clrbwbnzl clrbwibz clrbwibzl clrbwibnz clrbwibnzl
cmplwbc cmplwbcl cmpwbc cmpwbcl cmpwibc cmpwibcl
cmpwblt cmpwble cmpwbgt cmpwbge cmpwbeq cmpwbne
cmpwbltl cmpwblel cmpwbgtl cmpwbgel cmpwbeql cmpwbnel
cmpwiblt cmpwible cmpwibgt cmpwibge cmpwibeq cmpwibne
cmpwibltl cmpwiblel cmpwibgtl cmpwibgel cmpwibeql cmpwibnel
bwgez bwgezl bwgtz bwgtzl bwlez bwlezl bwltz bwltzl bwnz bwnzl bwz bwzl
""")
PPE42X_ADDITIONS = mnemonic_set("""
mulli mullw mullw. mullwo mullwo. rldicl rldicl. rldicr rldicr.
rldimi rldimi. slvd srvd
""")
PPE42XM_ADDITIONS = mnemonic_set("mulhw mulhw. mulhwu mulhwu.")

# The denylist is diagnostic only. The allowlist remains authoritative, and
# every mnemonic absent from it fails even when it is not named below.
DENYLIST_REASONS = {
    **{name: "condition-register logical instruction" for name in mnemonic_set(
        "crand crandc crclr creqv crmove crnand crnor crnot cror crorc crset crxor")},
    **{name: "unsupported synchronization instruction" for name in {"eieio", "isync"}},
    **{name: "system-call instruction" for name in {"sc", "scv"}},
    **{name: "string/multiple load-store instruction" for name in mnemonic_set(
        "lmw lswi lswx stmw stswi stswx")},
    **{name: "instruction-cache operation" for name in {"icbi", "icbt", "iccci"}},
    "mtcr": "selects all CR fields; PPE42 supports only mtcrf 128, RS (mtcr0)",
    "mtocrf": "bit 11 form is unsupported; use legacy mtcrf 128, RS (mtcr0)",
    "mulli": "PPE42X/PPE42XM instruction, not base PPE42",
    "mulhwu": "PPE42XM instruction, not base PPE42 or PPE42X",
}


def allowed_for_variant(variant: str) -> set[str]:
    allowed = set(PPE42_ALLOWLIST)
    if variant in {"ppe42x", "ppe42xm"}:
        allowed.update(PPE42X_ADDITIONS)
    if variant == "ppe42xm":
        allowed.update(PPE42XM_ADDITIONS)
    return allowed


def check_file(path: Path, allowed: set[str]) -> int:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as error:
        print(f"{path}: error: {error}", file=sys.stderr)
        return 1
    violations = decoded = 0
    for line_number, line in enumerate(lines, 1):
        match = INSTRUCTION_ROW.match(line)
        if not match:
            continue
        decoded += 1
        mnemonic = match.group("mnemonic").lower()
        if mnemonic not in allowed:
            reason = DENYLIST_REASONS.get(mnemonic, "not present in the reviewed allowlist")
            print(f"{path}:{line_number}: unsupported instruction "
                  f"'{mnemonic}': {reason}", file=sys.stderr)
            violations += 1
            continue

        # PPE42 implements only CR0. The architecture notes for bc, bcctr,
        # and bclr require instruction bits 11:13 (Power ISA MSB-first bit
        # numbering) to be 000. Check the encoding, not its alias spelling:
        # for example, `bt 2` is valid while `bt 6` is not.
        encoded = int.from_bytes(bytes.fromhex(match.group("bytes")), "big")
        primary_opcode = encoded >> 26
        extended_opcode = (encoded >> 1) & 0x3ff
        is_conditional_branch = primary_opcode == 16 or (
            primary_opcode == 19 and extended_opcode in {16, 528}
        )
        restricted_bits = (encoded >> (31 - 13)) & 0x7
        if is_conditional_branch and restricted_bits != 0:
            print(f"{path}:{line_number}: unsupported encoding for '{mnemonic}': "
                  f"PPE42 requires instruction bits 11:13 to be 000 "
                  f"(found {restricted_bits:03b}; only CR0 is implemented)",
                  file=sys.stderr)
            violations += 1

        # The four supported word-compare forms likewise require BF=0
        # (instruction bits 6:8), so that the result is written to CR0.
        is_word_compare = primary_opcode in {10, 11} or (
            primary_opcode == 31 and extended_opcode in {0, 32}
        )
        compare_field = (encoded >> (31 - 8)) & 0x7
        if is_word_compare and compare_field != 0:
            print(f"{path}:{line_number}: unsupported encoding for '{mnemonic}': "
                  f"PPE42 requires compare instruction bits 6:8 to be 000 "
                  f"(found {compare_field:03b}; only CR0 is implemented)",
                  file=sys.stderr)
            violations += 1

        # mtcr0 is encoded as the legacy mtcrf form with bit 11 clear and
        # FXM=0x80. Any other mask selects unimplemented CR fields; mtocrf
        # uses the unsupported bit-11 form.
        is_mtcr_form = primary_opcode == 31 and extended_opcode == 144
        mtcr_bit_11 = (encoded >> (31 - 11)) & 1
        mtcr_fxm = (encoded >> (31 - 19)) & 0xff
        if is_mtcr_form and (mtcr_bit_11 != 0 or mtcr_fxm != 0x80):
            print(f"{path}:{line_number}: unsupported encoding for '{mnemonic}': "
                  f"PPE42 requires legacy mtcrf with bit 11=0 and FXM=128 "
                  f"(found bit 11={mtcr_bit_11}, FXM={mtcr_fxm})",
                  file=sys.stderr)
            violations += 1
    if decoded == 0:
        print(f"{path}: error: no llvm-objdump instruction rows found", file=sys.stderr)
        return 1
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="strictly check every mnemonic against embedded PPE42 allowlists"
    )
    parser.add_argument("--variant", choices=("ppe42", "ppe42x", "ppe42xm"),
                        default="ppe42xm")
    parser.add_argument("disassembly", nargs="+", type=Path)
    args = parser.parse_args()
    allowed = allowed_for_variant(args.variant)
    violations = sum(check_file(path, allowed) for path in args.disassembly)
    if violations:
        print(f"PPE42 ISA check failed: {violations} unsupported or unclassified "
              "instruction(s)", file=sys.stderr)
        return 1
    print(f"PPE42 ISA check passed for {args.variant}: "
          f"{len(args.disassembly)} file(s), {len(allowed)} allowed mnemonics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
