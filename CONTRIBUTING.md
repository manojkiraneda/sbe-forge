# Contributing

## Integration changes

Firmware, documentation, tools, containers, and CI changes are made directly
in this repository.

## LLVM backend changes

1. Create a feature branch in the `llvm-project` submodule from
   `ppe42/llvm-21`.
2. Implement the change with LLVM CodeGen or MC regression tests.
3. Merge the change into the downstream LLVM branch.
4. Update and commit the `llvm-project` gitlink in SBE Forge.
5. Run `./scripts/dev.sh` before submitting the integration change.

The parent commit and submodule commit should be reviewed together. A parent
commit must never reference an LLVM commit that has not been pushed to the
configured submodule remote.

## Updating upstream LLVM

Create a new downstream branch for a major LLVM release. For patch releases,
rebase the existing downstream branch onto the new upstream tag, run LLVM's
PowerPC tests and the SBE Forge integration suite, then advance the submodule
pointer. Tag known-good compiler revisions before changing the supported base.
