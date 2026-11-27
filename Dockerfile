FROM fedora:45

# This dependency module changes independently of compiler/model build logic.
COPY llvm-project/utils/ppe42/toolchain-environment.sh /opt/ppe42-source/utils/ppe42/toolchain-environment.sh
ENV PATH="/opt/ppe42-python/bin:/root/.cargo/bin:${PATH}" \
    VIRTUAL_ENV=/opt/ppe42-python \
    SBE_LLVM_DEPS_DIR=/opt/ppe42-mlgo
RUN /opt/ppe42-source/utils/ppe42/toolchain-environment.sh deps && dnf clean all
RUN /opt/ppe42-source/utils/ppe42/toolchain-environment.sh prepare-tensorflow

# Compiler or model preparation changes do not invalidate the TensorFlow layer.
COPY llvm-project/utils/ppe42/build-toolchain.sh /opt/ppe42-source/utils/ppe42/build-toolchain.sh
RUN /opt/ppe42-source/utils/ppe42/build-toolchain.sh prepare-model

WORKDIR /workspace
CMD ["/bin/bash"]
