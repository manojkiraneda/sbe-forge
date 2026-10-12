#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
container_engine=${CONTAINER_ENGINE:-podman}
output_dir=${OUTPUT_DIR:-"${PWD}/qme-fedora44-output"}
cte_dir=${CTE_DIR:-}

if [[ -z "${cte_dir}" || ! -d "${cte_dir}/tools/ecmd/ver-16-5" ]]; then
    echo 'Set CTE_DIR to a host CTE tree containing tools/ecmd/ver-16-5.' >&2
    exit 1
fi
if [[ ! -d "${HOME}/.ssh" ]]; then
    echo 'The host ~/.ssh directory is required for the private GitHub clone.' >&2
    exit 1
fi
if [[ ! -s "${HOME}/.ssh/known_hosts" ]]; then
    echo 'Add github.ibm.com to ~/.ssh/known_hosts after verifying its key.' >&2
    exit 1
fi
if ! command -v "${container_engine}" >/dev/null; then
    echo "Container engine not found: ${container_engine}" >&2
    exit 1
fi

mkdir -p "${output_dir}"
output_dir=$(cd -- "${output_dir}" && pwd)
cte_dir=$(cd -- "${cte_dir}" && pwd)
if [[ -e "${output_dir}/hostfw" ]]; then
    echo "${output_dir}/hostfw already exists; use a fresh OUTPUT_DIR." >&2
    exit 1
fi

"${container_engine}" build --platform linux/amd64 \
    -t qme-fedora44 "${script_dir}"
"${container_engine}" run --rm --platform linux/amd64 \
    --security-opt label=disable \
    --mount "type=bind,src=${output_dir},dst=/work" \
    --mount "type=bind,src=${cte_dir},dst=/opt/cte,readonly" \
    --mount "type=bind,src=${HOME}/.ssh,dst=/root/.ssh,readonly" \
    qme-fedora44
