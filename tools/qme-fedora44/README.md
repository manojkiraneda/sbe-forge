# Build QME in Fedora 44

This launcher builds a small Fedora 44 image, runs it, downloads the latest
tagged PPE42 toolchain release with SHA-256 verification, checks out the
`qme_clang` branch of the private HostFW fork, and runs `./hfw ekb` followed
by `./ekb build qme`. The checkout and build output stay in `OUTPUT_DIR`.

EKB's `env.bash` requires IBM CTE. Provide an accessible host CTE tree; it
must contain `tools/ecmd/ver-16-5/bin/ecmdaliases.ksh`. The launcher mounts it
read-only at `/opt/cte`. The host machine's `~/.ssh` directory must contain a
key that can access `github.ibm.com` and a verified `known_hosts` entry. It is
mounted read-only while the container runs and is not added to the image.

```sh
export CTE_DIR=/path/to/cte
export OUTPUT_DIR="$PWD/qme-fedora44-output"  # optional
./tools/qme-fedora44/run.sh
```

Set `CONTAINER_ENGINE=docker` to use Docker instead of Podman. The runtime
requires an x86-64 host or an environment configured for amd64 emulation. The
current HostFW tree resets `PPETOOLS` during `./hfw ekb`; the build wrapper
sets it again after EKB workon has completed.
