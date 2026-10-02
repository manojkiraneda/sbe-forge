#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
toolchain_dir="${SBE_LLVM_INSTALL_DIR:-${repo_root}/../artifacts/ppe42-toolchain}"
cross_file="${repo_root}/build/ppe42-stack.ini"

for program in clang ld.lld llvm-ar llvm-objcopy llvm-objdump; do
  if [[ ! -x "${toolchain_dir}/bin/${program}" ]]; then
    echo "Missing ${toolchain_dir}/bin/${program}" >&2
    exit 1
  fi
done
if [[ ! -f "${toolchain_dir}/lib/ppe42/libclang_rt.ppe42.a" ]]; then
  echo "Missing PPE42 runtime in ${toolchain_dir}" >&2
  exit 1
fi

# Meson caches the compiler path and Ninja does not rebuild source merely
# because the binary at that path changed. Give each compiler its own build.
toolchain_id="$(sha256sum "${toolchain_dir}/bin/clang" | cut -c1-12)"
build_dir="${repo_root}/build/firmware-stack-ops-${toolchain_id}"

mkdir -p "${repo_root}/build"
sed "s#/opt/llvm-install#${toolchain_dir}#g" \
  "${repo_root}/firmware/cross/ppe42.ini" > "${cross_file}"

export PATH="${toolchain_dir}/bin:${PATH}"
if [[ -f "${build_dir}/meson-private/coredata.dat" ]]; then
  meson setup "${build_dir}" "${repo_root}/firmware" \
    --cross-file "${cross_file}" -Dapp=test_stack_ops --reconfigure
else
  meson setup "${build_dir}" "${repo_root}/firmware" \
    --cross-file "${cross_file}" -Dapp=test_stack_ops
fi

meson test -C "${build_dir}" --print-errorlogs ppe42-stack-ops ppe42-isa
meson compile -C "${build_dir}"
echo "Firmware: ${build_dir}/test_stack_ops.bin"
echo "Disassembly: ${build_dir}/test_stack_ops.dis"
