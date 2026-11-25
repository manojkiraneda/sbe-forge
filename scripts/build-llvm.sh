#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="${SBE_LLVM_SOURCE_DIR:-${repo_root}/llvm-project}"
driver="${source_dir}/utils/ppe42/build-toolchain.sh"
if [[ ! -x "$driver" ]]; then
  echo 'Shared LLVM build driver is missing; run: git submodule update --init --recursive' >&2
  exit 1
fi
export SBE_LLVM_BUILD_DIR="${SBE_LLVM_BUILD_DIR:-${repo_root}/build/llvm}"
export SBE_LLVM_INSTALL_DIR="${SBE_LLVM_INSTALL_DIR:-${repo_root}/build/toolchain}"
exec "$driver" "$@"
