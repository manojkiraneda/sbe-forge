#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

"${repo_root}/scripts/build-llvm.sh"
"${repo_root}/scripts/test-firmware.sh"
