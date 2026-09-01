# SBE Forge

SBE Forge is the integration workspace for the PPE42 LLVM toolchain, firmware
runtime, example applications, and ISA-conformance checks.

The downstream compiler is maintained as ordinary commits in the
`llvm-project` submodule. This repository pins one tested compiler commit and
contains no patch-application or LLVM source-download machinery.

## Repository layout

```text
llvm-project/   PPE42 LLVM fork, pinned as a Git submodule
firmware/       startup, runtime, applications, and native tests
tools/          disassembly and compiler-debug analysis tools
docs/           PPE42 ISA notes and backend documentation
scripts/        reproducible build and validation entry points
```

## Clone and build

```sh
git clone --recurse-submodules <sbe-forge-url>
cd sbe-forge
./scripts/dev.sh
```

If the repository was cloned without submodules:

```sh
git submodule update --init --recursive
```

`scripts/dev.sh` builds a development container, compiles LLVM/Clang/LLD,
builds the firmware applications, runs native tests, and validates every
generated disassembly against the PPE42XM rules. This source build is intended
for compiler development and reproducibility checks.

CI and application-only development consume the immutable compiler release in
`toolchain.lock`:

```sh
./scripts/fetch-toolchain.sh
./scripts/test-firmware.sh
```

The lock records the release, LLVM commit, asset name, and SHA-256 checksum.
Candidate compiler changes are tested against this repository by the PPE42
workflow in `sbe-forge-llvm-project` before they are tagged and published.

## Updating the compiler

Make backend changes inside `llvm-project` on `ppe42/llvm-21`, commit and push
them to the LLVM fork, and then commit the updated submodule pointer here.
Never copy backend changes into this repository as patch files.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the release and upstream-update
workflow.
