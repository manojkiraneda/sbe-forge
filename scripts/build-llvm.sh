#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${SBE_LLVM_BUILD_DIR:-${repo_root}/build/llvm}"
install_dir="${SBE_LLVM_INSTALL_DIR:-${repo_root}/build/toolchain}"

if [[ ! -f "${repo_root}/llvm-project/llvm/CMakeLists.txt" ]]; then
  echo "LLVM submodule is missing; run: git submodule update --init --recursive" >&2
  exit 1
fi

cmake -S "${repo_root}/llvm-project/llvm" -B "${build_dir}" -G Ninja \
  -DLLVM_ENABLE_PROJECTS='clang;lld' \
  -DLLVM_TARGETS_TO_BUILD=PowerPC \
  -DLLVM_ENABLE_ASSERTIONS=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="${install_dir}"
cmake --build "${build_dir}"
cmake --install "${build_dir}"

echo "PPE42 LLVM installed in ${install_dir}"
