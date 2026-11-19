FROM fedora:45

# Bootstrap only: the pinned LLVM driver owns build dependencies and MLGO.
RUN dnf install -y git python3.11 python3-pip ca-certificates && dnf clean all
COPY llvm-project/utils/ppe42/build-toolchain.sh /opt/ppe42-source/utils/ppe42/build-toolchain.sh
ENV PATH="/opt/ppe42-python/bin:/root/.cargo/bin:${PATH}" \
    VIRTUAL_ENV=/opt/ppe42-python \
    SBE_LLVM_DEPS_DIR=/opt/ppe42-mlgo
RUN /opt/ppe42-source/utils/ppe42/build-toolchain.sh deps \
    && /opt/ppe42-source/utils/ppe42/build-toolchain.sh prepare \
    && dnf clean all

WORKDIR /workspace
CMD ["/bin/bash"]
