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

# The PPE42 builtins are maintained in compiler-rt, but compiler-rt is not
# enabled as an LLVM runtime because its generic PowerPC target does not
# describe the PPE42 ABI. Build the PPE42-specific assembly helpers directly
# and install the archive at the location consumed by firmware/meson.build.
runtime_build_dir="${build_dir}/ppe42-runtime"
runtime_install_dir="${install_dir}/lib/ppe42"
runtime_sources=(
  "${repo_root}/llvm-project/compiler-rt/lib/builtins/ppc/ppe42-div32.S"
  "${repo_root}/llvm-project/compiler-rt/lib/builtins/ppc/ppe42-div64.S"
)
runtime_objects=()
mkdir -p "${runtime_build_dir}" "${runtime_install_dir}"
for source in "${runtime_sources[@]}"; do
  object="${runtime_build_dir}/$(basename "${source}" .S).o"
  "${install_dir}/bin/clang" -target powerpc-unknown-elf -mcpu=ppe42 \
    -msoft-float -ffreestanding -fno-builtin -c "${source}" -o "${object}"
  runtime_objects+=("${object}")
done
"${install_dir}/bin/llvm-ar" rcs \
  "${runtime_install_dir}/libclang_rt.ppe42.a" "${runtime_objects[@]}"

echo "PPE42 LLVM installed in ${install_dir}"
