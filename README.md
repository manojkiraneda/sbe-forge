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

The development container and LLVM release CI use the same build driver,
`llvm-project/utils/ppe42/build-toolchain.sh`. The container uses Fedora 45 and
Python 3.11; it caches TensorFlow AOT dependencies and the checksum-verified
inliner model in an image layer. Compiler objects remain in `build/llvm` and
the release-layout toolchain is staged in `build/toolchain`.

For native builds, install Python 3.11, run the shared driver with `deps` to
install host dependencies, then run `./scripts/build-llvm.sh`. The default
build includes an MLGO compilation smoke check and produces a toolchain archive.
`SBE_LLVM_BUILD_DIR`, `SBE_LLVM_INSTALL_DIR` and `SBE_LLVM_DEPS_DIR` override
the build, staging and dependency directories. Individual phases are listed by
`./scripts/build-llvm.sh --help`. Build configuration changes belong in the
shared driver; updating the LLVM submodule brings them into this repository.
