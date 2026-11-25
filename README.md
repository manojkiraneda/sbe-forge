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
coredump/       Simics SPPE core capture script and LLDB instructions
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

`scripts/dev.sh` builds a development container, compiles LLVM/Clang/LLD/LLDB with the embedded MLGO inliner,
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

See [coredump/README.md](coredump/README.md) for capturing Odyssey SPPE cores
from Simics and inspecting PK threads with LLDB.

### Development entry point

`dev.sh` is the common entry point for local builds and LLVM toolchain CI.
The default runs in Fedora; `--native` uses the current host, including macOS.
The full build compiles/packages the toolchain and then tests firmware:

```sh
./scripts/dev.sh
./scripts/dev.sh --native
```

Native hosts need the dependencies installed first (`--native --phase deps`)
and Python 3.11 for MLGO. Run one phase while iterating, or use an existing
compiler for firmware-only testing:

```sh
./scripts/dev.sh --native --phase configure -- -DCMAKE_VERBOSE_MAKEFILE=ON
./scripts/dev.sh --native --phase build
./scripts/dev.sh --native --phase runtime
./scripts/dev.sh --native --phase stage
./scripts/dev.sh --native --phase check
./scripts/dev.sh --native --phase firmware
```

`--llvm-source /path/to/llvm-project` selects a candidate checkout without
updating its submodule or switching its revision. `--build-dir` and
`--install-dir` select the compiler build tree and staged toolchain. Existing
`SBE_LLVM_*` overrides still work. Relative paths are resolved from the calling
directory. `--engine podman` selects a different container engine.

LLVM CI calls the native phases around its existing caches and compiler
regression checks, then runs the container `check` phase on Linux x86 to validate
the development image and packaged compiler together without rebuilding LLVM.
The command-routing tests cover native and container modes, phase selection,
path overrides, failure propagation and compiler-before-firmware ordering.
After updating a pinned submodule revision, run
`git submodule update --init --recursive` before the development build.
