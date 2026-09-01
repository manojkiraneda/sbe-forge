#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
firmware_dir="${repo_root}/firmware"
build_dir="${repo_root}/build/firmware"
toolchain_dir="${SBE_LLVM_INSTALL_DIR:-${repo_root}/build/toolchain}"
cross_file="${repo_root}/build/ppe42.ini"

mkdir -p "${repo_root}/build"
sed "s#/opt/llvm-install#${toolchain_dir}#g" \
  "${firmware_dir}/cross/ppe42.ini" > "${cross_file}"

export PATH="${toolchain_dir}/bin:${PATH}"
export SBE_LLVM_INSTALL_DIR="${toolchain_dir}"

if [[ -f "${build_dir}/meson-private/coredata.dat" ]]; then
  meson setup "${build_dir}" "${firmware_dir}" --cross-file "${cross_file}" \
    --reconfigure
else
  meson setup "${build_dir}" "${firmware_dir}" --cross-file "${cross_file}"
fi
meson test -C "${build_dir}" --print-errorlogs
meson compile -C "${build_dir}"
