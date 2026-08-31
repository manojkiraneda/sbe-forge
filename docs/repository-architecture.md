# Repository architecture

SBE Forge deliberately separates compiler development from toolchain
integration.

## Repositories

### `sbe-forge`

Owns firmware, runtime code, ISA policy, complete-image validation, build
containers, and CI. Its `llvm-project` entry is a gitlink to one tested LLVM
revision.

### `sbe-forge-llvm-project`

Is a fork of upstream LLVM. The `ppe42/llvm-21` branch is based on the
`llvmorg-21.1.4` release and carries the PPE42 backend as normal Git commits.
Backend changes, LLVM unit tests, and LLVM CodeGen/MC regression tests belong
there.

## Dependency direction

The integration repository depends on an immutable LLVM commit. The LLVM fork
must not depend on files from SBE Forge, and CI must not modify the submodule.
This makes a parent commit reproducible and allows compiler changes to be
reviewed, rebased, bisected, and tested independently.

## Release process

1. Merge and push an LLVM backend change.
2. Run the LLVM PowerPC test suite on the downstream branch.
3. Advance the `llvm-project` gitlink in SBE Forge.
4. Build every firmware image and run the disassembly validator.
5. Tag the SBE Forge commit and, when useful, the corresponding LLVM commit.

Both repositories must be published under the same Git hosting owner if the
relative submodule URL (`../sbe-forge-llvm-project`) is retained.
