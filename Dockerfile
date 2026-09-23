FROM ubuntu:25.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    build-essential \
    ccache \
    cmake \
    ninja-build \
    meson \
    git \
    python3 \
    python3-pip \
    python3-setuptools \
    rustup \
    zstd \
    libffi-dev \
    libedit-dev \
    libncurses-dev \
    zlib1g-dev \
    libxml2-dev \
    libssl-dev \
    vim \
    file \
    bsdmainutils \
    gcc-powerpc-linux-gnu \
    g++-powerpc-linux-gnu \
    binutils-powerpc-linux-gnu \
    && rm -rf /var/lib/apt/lists/*

# Match the CI Rust toolchain used by the firmware build.
RUN rustup toolchain install stable --profile minimal \
    && rustup default stable \
    && rustup target add powerpc-unknown-linux-gnu

ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /workspace
CMD ["/bin/bash"]
