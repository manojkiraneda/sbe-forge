#!/usr/bin/env bash
set -euo pipefail

release_base=https://github.com/manojkiraneda/sbe-forge-llvm-project/releases/latest/download
asset=sbe-ppe42-toolchain-linux-x86_64.tar.zst
toolchain_dir=/opt/ppe42-toolchain
checkout_dir=/work/hostfw

if [[ ! -f "${CTEPATH}/tools/ecmd/ver-16-5/bin/ecmdaliases.ksh" ]]; then
    echo "EKB needs a CTE tree at ${CTEPATH} (including ecmd/ver-16-5)." >&2
    exit 1
fi
if [[ ! -s /root/.ssh/known_hosts ]]; then
    echo 'A trusted known_hosts file for github.ibm.com is required.' >&2
    exit 1
fi

export USER="${USER:-root}"
export LOGNAME="${LOGNAME:-root}"

git config --global user.name "${GIT_USER_NAME:-Manojkiran Eda}"
git config --global user.email "${GIT_USER_EMAIL:-manojeda@ibm.com}"

mkdir -p "${toolchain_dir}" /work
cd /tmp
curl --fail --location --retry 3 --show-error --silent \
    "${release_base}/${asset}" -o "${asset}"
curl --fail --location --retry 3 --show-error --silent \
    "${release_base}/${asset}.sha256" -o "${asset}.sha256"
sha256sum --check "${asset}.sha256"
tar --zstd -xf "${asset}" -C /opt
test -x "${toolchain_dir}/bin/clang"
"${toolchain_dir}/bin/clang" --version | head -1

if [[ -e "${checkout_dir}" ]]; then
    echo "${checkout_dir} already exists; use an empty output directory." >&2
    exit 1
fi
GIT_SSH_COMMAND='ssh -o StrictHostKeyChecking=yes' \
    git clone --branch qme_clang --single-branch \
        git@github.ibm.com:manojeda/hostfw.git "${checkout_dir}"

# hfw/ekb both exec a new $SHELL. This wrapper runs only after EKB has sourced
# its environment, which would otherwise replace PPETOOLS with /usr/local/ppe42.
cat >/tmp/ekb-build-shell <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export USER="${USER:-root}"
export LOGNAME="${LOGNAME:-root}"
export SHELL=/bin/bash
export PPETOOLS=/opt/ppe42-toolchain
export PATH="${PPETOOLS}/bin:${PATH}"
export LD_LIBRARY_PATH="${PPETOOLS}/lib:${LD_LIBRARY_PATH:-}"
cd "${EKB_ROOT}"
exec ./ekb build qme
EOF
chmod 0755 /tmp/ekb-build-shell

cd "${checkout_dir}"
export PPETOOLS="${toolchain_dir}"
export SHELL=/tmp/ekb-build-shell
./hfw ekb
