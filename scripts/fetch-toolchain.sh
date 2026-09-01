#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
lock_file="${SBE_TOOLCHAIN_LOCK:-${repo_root}/toolchain.lock}"
install_dir="${SBE_LLVM_INSTALL_DIR:-${repo_root}/build/toolchain}"
download_root="${SBE_TOOLCHAIN_DOWNLOAD_DIR:-${repo_root}/build/downloads}"

if [[ ! -f "${lock_file}" ]]; then
  echo "Missing toolchain lock: ${lock_file}" >&2
  exit 1
fi

declare -A lock
while IFS='=' read -r key value; do
  [[ -z "${key}" || "${key}" == \#* ]] && continue
  lock["${key}"]="${value}"
done < "${lock_file}"

for key in repository version llvm_sha asset sha256; do
  if [[ -z "${lock[${key}]:-}" || "${lock[${key}]}" == TO_BE_SET_* ]]; then
    echo "Invalid ${key} in ${lock_file}" >&2
    exit 1
  fi
done

download_dir="${download_root}/${lock[version]}"
mkdir -p "${download_dir}" "$(dirname -- "${install_dir}")"
archive="${download_dir}/${lock[asset]}"

if [[ ! -f "${archive}" ]]; then
  gh release download "${lock[version]}" \
    --repo "${lock[repository]}" \
    --pattern "${lock[asset]}" \
    --dir "${download_dir}"
fi

actual_sha="$(sha256sum "${archive}" | awk '{print $1}')"
if [[ "${actual_sha}" != "${lock[sha256]}" ]]; then
  echo "Toolchain checksum mismatch: expected ${lock[sha256]}, got ${actual_sha}" >&2
  exit 1
fi

rm -rf "${install_dir}"
mkdir -p "${install_dir}"
tar --zstd -xf "${archive}" -C "${install_dir}" --strip-components=1

manifest_sha="$(sed -n 's/.*"llvm_sha": "\([0-9a-f]*\)".*/\1/p' "${install_dir}/manifest.json")"
if [[ "${manifest_sha}" != "${lock[llvm_sha]}" ]]; then
  echo "Toolchain manifest revision mismatch: expected ${lock[llvm_sha]}, got ${manifest_sha}" >&2
  exit 1
fi

echo "Installed ${lock[version]} (${manifest_sha}) in ${install_dir}"
