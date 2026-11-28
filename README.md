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

`dev.sh` is the common build-and-test entry point used locally and by LLVM CI.
Its default container build installs dependencies, builds Clang/LLD/LLDB with
MLGO, runs the compiler regressions, stages and checks the toolchain, builds/tests
firmware and its disassembly, then creates the archive only after validation
succeeds.

TensorFlow is installed in a cached base-image layer. Model download/extraction
is a later layer; a failure there preserves the installed TensorFlow wheel.
Compiler/model script changes do not invalidate the stable dependency layers.
Preparation also validates and reuses an installed TensorFlow version instead
of running pip again. Container ccache data persists under the selected compiler
build directory.

### Native builds and individual phases

Use `--native` on a configured host, including macOS. Native hosts need Python
3.11 and the build dependencies; `--native --phase deps` installs the supported
host dependencies. The default container supplies these automatically.

```sh
./scripts/dev.sh --native
./scripts/dev.sh --native --phase test
./scripts/dev.sh --native --phase configure -- -DCMAKE_VERBOSE_MAKEFILE=ON
./scripts/dev.sh --native --phase build
./scripts/dev.sh --native --phase test-compiler
./scripts/dev.sh --native --phase test-package
./scripts/dev.sh --native --phase firmware
```

The `test` phase reruns the entry-point, compiler, package and firmware checks
against an existing build. The complete `all` phase runs these around the build
steps in dependency order. Additional phases include `prepare-tensorflow`,
`prepare-model`, `runtime`, `stage`, `check`, `archive`, `host`, `cache-start`
and `cache-report`; see `./scripts/dev.sh --help` for the full list.

`--llvm-source /path/to/llvm-project` selects an existing candidate checkout
without updating its submodule or switching its revision. `--build-dir` and
`--install-dir` override the compiler build tree and staged toolchain.
`SBE_LLVM_*` overrides remain supported; relative paths use the calling
directory. `--engine podman` selects another container engine. Use separate
build directories when switching between native and container environments.

### Application-only development

Use the immutable release in `toolchain.lock` to test applications without
building the compiler:

```sh
./scripts/dev.sh --native --phase fetch
./scripts/dev.sh --native --phase firmware
```

The lock records the release, compiler commit, asset and SHA-256 checksum.

### CI responsibilities

LLVM CI calls `dev.sh` phases for dependency preparation, configuration, build,
regression tests, packaging and firmware validation. Test lists and fixtures
live in the shared LLVM scripts, so local `all`/`test` uses the same checks.
CI retains runner selection, checkouts, cache restore/save, artifact upload,
attestation and tagged release publication. Linux x86 also runs the actual
container `check` phase against the staged candidate without rebuilding LLVM.

## Updating the compiler

Make backend changes inside `llvm-project` on `ppe42/llvm-21`, commit and push
them to the LLVM fork, and then commit the updated submodule pointer here.
Never copy backend changes into this repository as patch files.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the release and upstream-update
workflow.

See [coredump/README.md](coredump/README.md) for capturing Odyssey SPPE cores
from Simics and inspecting PK threads with LLDB.

Select the container base and the compiler used to build the toolchain with:

```sh
./scripts/dev.sh --container --base-image fedora:45 --host-compiler clang
```

`--host-compiler` also accepts `gcc` or `system` (the default), and works with
`--native`. It selects the host compiler, not the PPE42 target compiler. The
base image must support the shared dependency installer (Fedora or Ubuntu/Debian)
and provide Python 3.11. Use a separate `--build-dir` when changing compilers.
The corresponding environment overrides are `SBE_LLVM_BASE_IMAGE` and
`SBE_LLVM_HOST_COMPILER`.
