#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
image="sbe-forge-dev:latest"

git -C "${repo_root}" submodule update --init --recursive
docker build -t "${image}" "${repo_root}"
docker run --rm \
  --volume "${repo_root}:/workspace:Z" \
  --workdir /workspace \
  --env SBE_LLVM_BUILD_DIR=/workspace/build/llvm \
  --env SBE_LLVM_INSTALL_DIR=/workspace/build/toolchain \
  "${image}" ./scripts/ci.sh
