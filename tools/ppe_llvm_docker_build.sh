#!/usr/bin/env bash

# The PPE42 toolchain (a GitHub Actions artifact, which needs authentication)
# is installed into the image at build time using a github.com token passed as
# the build secret 'gh_token': GH_TOKEN/GITHUB_TOKEN, else 'gh auth token'.
# Override the source with TOOLCHAIN_REPO / TOOLCHAIN_RUN_ID.
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
container_engine=${CONTAINER_ENGINE:-podman}
image=${HOSTFWCI_IMAGE:-ppe-llvm-fedora45}

if ! command -v "${container_engine}" >/dev/null; then
    echo "Container engine not found: ${container_engine}" >&2
    exit 1
fi

case "$(uname -m)" in
    arm64|aarch64) platform=linux/arm64 ;;
    x86_64|amd64)  platform=linux/amd64 ;;
    *) echo "Unsupported host architecture: $(uname -m)" >&2; exit 1 ;;
esac

token=${GH_TOKEN:-${GITHUB_TOKEN:-}}
if [[ -z "${token}" ]] && command -v gh >/dev/null; then
    echo "[ppe-llvm-build] + gh auth token --hostname github.com" >&2
    token=$(gh auth token --hostname github.com 2>/dev/null || true)
fi
if [[ -z "${token}" ]]; then
    echo 'No github.com token: run "gh auth login --hostname github.com" or set GH_TOKEN.' >&2
    exit 1
fi

build_args=()
[[ -n "${TOOLCHAIN_REPO:-}" ]] && build_args+=(--build-arg "TOOLCHAIN_REPO=${TOOLCHAIN_REPO}")
[[ -n "${TOOLCHAIN_RUN_ID:-}" ]] && build_args+=(--build-arg "TOOLCHAIN_RUN_ID=${TOOLCHAIN_RUN_ID}")

# Name the platform explicitly (and re-pull the base if the local copy is for
# another architecture) so a previously pulled amd64 base image is not reused.
echo "[ppe-llvm-build] + ${container_engine} build --platform ${platform} --secret id=gh_token -f ppe_llvm_container_file -t ${image} ${build_args[*]:-}" >&2
GH_BUILD_TOKEN="${token}" "${container_engine}" build \
    --platform "${platform}" --pull=newer \
    --secret id=gh_token,env=GH_BUILD_TOKEN \
    ${build_args[@]+"${build_args[@]}"} \
    -f "${script_dir}/ppe_llvm_container_file" \
    -t "${image}" "${script_dir}"
echo "[ppe-llvm-build] image architecture: $("${container_engine}" image inspect "${image}" --format '{{.Architecture}}')" >&2
