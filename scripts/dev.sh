#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mode=container
phase=all
source_dir="${SBE_LLVM_SOURCE_DIR:-${repo_root}/llvm-project}"
build_dir="${SBE_LLVM_BUILD_DIR:-${BUILD_DIR:-${repo_root}/build/llvm}}"
install_dir="${SBE_LLVM_INSTALL_DIR:-${PACKAGE_DIR:-${repo_root}/build/toolchain}}"
expected_arch="${SBE_LLVM_EXPECTED_ARCH:-}"
engine=docker
image=sbe-forge-dev:latest
cmake_args=()
cmake_arg_count=0
usage() {
  cat <<'HELP'
Usage: scripts/dev.sh [options] [-- CMake arguments]
  --native                 Run directly on the host (default: container)
  --container              Run in the Fedora development container
  --phase PHASE            all (default), deps, prepare, prepare-tensorflow,
                           prepare-model, configure, build-deps, build, runtime,
                           stage, check, test, test-entrypoint, test-unit,
                           test-compiler, test-package, firmware, fetch, host,
                           cache-start, cache-report, or archive
  --expect-arch ARCH        Verify native host architecture (host/all phases)
  --llvm-source DIR        Use this LLVM checkout without updating a submodule
  --build-dir DIR          Compiler build tree
  --install-dir DIR        Staged toolchain consumed by firmware tests
  --engine COMMAND         Container engine (default: docker)
  --image NAME             Development image name
  -h, --help               Show this help

The all phase builds the compiler, runs the same compiler/package regressions
as CI, packages it, then builds/tests firmware. The test phase reruns checks
against an existing compiler build and staged toolchain.
Existing SBE_LLVM_* overrides are supported. BUILD_DIR and PACKAGE_DIR are
accepted for CI. CMake arguments are accepted with all or configure only.
HELP
}
while (( $# )); do
  case "$1" in
    --native) mode=native; shift;;
    --container) mode=container; shift;;
    --phase|--llvm-source|--build-dir|--install-dir|--engine|--image|--expect-arch)
      if (( $# < 2 )) || [[ -z "$2" ]]; then echo "Missing value for $1" >&2; exit 2; fi
      case "$1" in
        --phase) phase="$2";;
        --expect-arch) expected_arch="$2";;
        --llvm-source) source_dir="$2";;
        --build-dir) build_dir="$2";;
        --install-dir) install_dir="$2";;
        --engine) engine="$2";;
        --image) image="$2";;
      esac
      shift 2;;
    --) shift; cmake_arg_count=$#; cmake_args=("$@"); break;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2;;
  esac
done
case "$phase" in
  all|deps|prepare|prepare-tensorflow|prepare-model|configure|build-deps|build|runtime|stage|check|archive|firmware|fetch|test|test-entrypoint|test-unit|test-compiler|test-package|host|cache-start|cache-report) ;;
  *) echo "Unknown phase: $phase" >&2; exit 2;;
esac
if (( cmake_arg_count )) && [[ "$phase" != all && "$phase" != configure ]]; then
  echo 'CMake arguments require --phase all or --phase configure' >&2; exit 2
fi
# Resolve overrides before either script changes directory. Keep identical paths
# inside containers so compiler caches and user-selected outputs remain usable.
absolute() {
  local path="$1" part result=/
  local components=()
  case "$path" in /*) ;; *) path="$PWD/$path";; esac
  IFS=/ read -r -a components <<< "$path"
  for part in ${components[@]+"${components[@]}"}; do
    case "$part" in
      ''|.) ;;
      ..) result="${result%/*}";;
      *) result="${result%/}/$part";;
    esac
  done
  printf '%s\n' "${result:-/}"
}
source_dir="$(absolute "$source_dir")"
build_dir="$(absolute "$build_dir")"
install_dir="$(absolute "$install_dir")"
export SBE_LLVM_SOURCE_DIR="$source_dir"
export SBE_LLVM_BUILD_DIR="$build_dir"
export SBE_LLVM_INSTALL_DIR="$install_dir"
export SBE_LLVM_EXPECTED_ARCH="$expected_arch"

if [[ "$mode" == container || ("$phase" != firmware && "$phase" != fetch && "$phase" != test-entrypoint) ]]; then
  driver="$source_dir/utils/ppe42/build-toolchain.sh"
  if [[ ! -x "$driver" && "$source_dir" == "$repo_root/llvm-project" ]]; then
    git -C "$repo_root" submodule update --init --recursive --depth 1 --filter=blob:none --progress
  fi
  if [[ ! -x "$driver" ]]; then echo "Shared build driver not found: $driver" >&2; exit 1; fi
fi

load_host_environment() {
  if [[ -f "$source_dir/utils/ppe42/toolchain-environment.sh" ]]; then
    source "$source_dir/utils/ppe42/toolchain-environment.sh"
    initialize
  fi
}

test_entrypoint() (
  load_host_environment
  python3 -m unittest discover -s "$repo_root/tests" -p 'test_*build*.py' -v
)

test_firmware() (
  load_host_environment
  exec "$repo_root/scripts/test-firmware.sh"
)

if [[ "$mode" == native ]]; then
  if [[ "$phase" == fetch ]]; then
    exec "$repo_root/scripts/fetch-toolchain.sh"
  elif [[ "$phase" == test-entrypoint ]]; then
    test_entrypoint
    exit
  elif [[ "$phase" == all || "$phase" == test ]]; then
    test_entrypoint
    "$repo_root/scripts/build-llvm.sh" "$phase" ${cmake_args[@]+"${cmake_args[@]}"}
    test_firmware
    exit
  elif [[ "$phase" == firmware ]]; then
    test_firmware
    exit
  else
    exec "$repo_root/scripts/build-llvm.sh" "$phase" ${cmake_args[@]+"${cmake_args[@]}"}
  fi
fi

# Only the selected driver's source is needed to prepare the image. This also
# lets LLVM CI test its candidate checkout rather than the submodule's pin.
context="$(mktemp -d)"
trap 'rm -rf -- "$context"' EXIT
mkdir -p "$context/llvm-project/utils/ppe42" "$build_dir" "$install_dir"
cp "$driver" "$context/llvm-project/utils/ppe42/build-toolchain.sh"
cp "$source_dir/utils/ppe42/toolchain-environment.sh" "$context/llvm-project/utils/ppe42/toolchain-environment.sh"
"$engine" build --file "$repo_root/Dockerfile" --tag "$image" "$context"
# Preserve /workspace for existing local CMake build trees. External CI paths
# are mounted unchanged, allowing the packaged candidate to be checked as-is.
container_path() {
  case "$1" in
    "$repo_root") printf '/workspace\n';;
    "$repo_root"/*) printf '/workspace/%s\n' "${1#"$repo_root"/}";;
    *) printf '%s\n' "$1";;
  esac
}
container_args=(--rm --volume "$repo_root:/workspace:Z" --workdir /workspace
  --env "CCACHE_DIR=$(container_path "$build_dir")/ccache")
for directory in "$source_dir" "$build_dir" "$install_dir"; do
  mapped="$(container_path "$directory")"
  if [[ "$mapped" == "$directory" ]]; then
    container_args+=(--volume "$directory:$directory:Z")
  fi
done
if [[ -n "$expected_arch" ]]; then
  container_args+=(--env "SBE_LLVM_EXPECTED_ARCH=$expected_arch")
fi
if [[ -n "${SBE_LLVM_DEPS_DIR:-}" ]]; then
  deps_dir="$(absolute "$SBE_LLVM_DEPS_DIR")"
  mkdir -p "$deps_dir"
  container_args+=(--volume "$deps_dir:$deps_dir:Z" --env "SBE_LLVM_DEPS_DIR=$deps_dir")
fi
"$engine" run "${container_args[@]}" "$image" "/workspace/scripts/dev.sh" \
  --native --phase "$phase" --llvm-source "$(container_path "$source_dir")" \
  --build-dir "$(container_path "$build_dir")" --install-dir "$(container_path "$install_dir")" \
  -- ${cmake_args[@]+"${cmake_args[@]}"}
