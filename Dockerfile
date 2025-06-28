# Start from Ubuntu 22.04 LTS
FROM ubuntu:22.04

# Set environment variables to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV RUSTUP_HOME=/usr/local/rustup
ENV CARGO_HOME=/usr/local/cargo
ENV PATH=/root/.local/bin:/usr/local/cargo/bin:$PATH

# Add virtual environment to PATH
# ENV PATH="/MoveXEther/cross_vm_demos/venv/bin:$PATH"

# Set working directory
WORKDIR /MoveXEther

# Install system dependencies, Rust, and Python
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    cmake \
    clang \
    git \
    pkg-config \
    libssl-dev \
    libpq-dev \
    binutils \
    lld \
    procps \
    net-tools \
    ca-certificates \
    python3 \
    python3-pip \
    python3-venv \
    unzip \
    libc6 \
    libc6-dev \
    libsqlite3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 18.15.0 using nvm
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash \
    && export NVM_DIR="$HOME/.nvm" \
    && [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" \
    && [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" \
    && nvm install 18.15.0 \
    && nvm use 18.15.0 \
    && nvm alias default 18.15.0 \
    && node --version \
    && npm --version

# Install Rust using rustup
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain 1.80.1 --profile minimal \
    && . $CARGO_HOME/env \
    && rustup target add x86_64-unknown-linux-gnu \
    && cargo --version \
    && rustc --version

# Install Aptos CLI from host
COPY aptos /root/.local/bin/aptos
RUN chmod +x /root/.local/bin/aptos
RUN aptos --version

# Copy both MoveEth and aptos-core projects
COPY MoviEth/ ./MoviEth/
COPY aptos-core/ ./aptos-core/

# Copy EVoM-cfx-rust-oopsla24 project
COPY EVoM-cfx-rust-oopsla24/ ./EVoM-cfx-rust-oopsla24/

# Copy cross-vm-demos folder (excluding existing node_modules)
COPY cross_vm_demos/ ./cross_vm_demos/


RUN /usr/bin/python3 -m venv venv 
RUN . ./cross_vm_demos/venv/bin/activate
RUN /usr/bin/python3 -m pip install --upgrade pip 
RUN pip3 install -r ./cross_vm_demos/requirements.txt

# Build EVoM-cfx-rust-oopsla24
RUN . $CARGO_HOME/env \
    && cd EVoM-cfx-rust-oopsla24 \
    && cargo build --release

# Install node_modules in the specified folders
RUN export NVM_DIR="$HOME/.nvm" \
    && [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" \
    && [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" \
    && cd /MoveXEther/cross_vm_demos/native_and_erc20_tokens_experiments/conflux_experiments && npm ci && \
    cd /MoveXEther/cross_vm_demos/evm-side/compound-eth-native && npm ci && \
    cd /MoveXEther/cross_vm_demos/evm-side/cross-erc-20 && npm ci && \
    cd /MoveXEther/cross_vm_demos/evm-side/uniswap-eth-native && npm ci && \
    cd /MoveXEther/cross_vm_demos/evm-side/swap-evm-double-dex && npm ci && \
    cd /MoveXEther/cross_vm_demos/evm-side/eth-erc-20 && npm ci && \
    cd /MoveXEther/cross_vm_demos/evm-side/uniswap-eth-cross && npm ci && \
    cd /MoveXEther/cross_vm_demos/evm-side/uniswap-and-pancake-eth-cross && npm ci && \
    cd /MoveXEther/cross_vm_demos/evm-side/compound-eth-cross && npm ci && \
    cd /MoveXEther/cross_vm_demos/evm-side/swap-evm && npm ci && \
    cd /MoveXEther/cross_vm_demos/cfx_cross_chain/core_space && npm ci && \
    cd /MoveXEther/cross_vm_demos/cfx_cross_chain/espace && npm ci

ENV PATH="$PATH:$NVM_DIR/versions/node/v18.17.1/bin"


# # # Build the aptos binary from MoviEth
# RUN . $CARGO_HOME/env \
#     && cd MoviEth \
#     && RUSTFLAGS=-Awarnings cargo build --release -p aptos

# # # Build the aptos binary from aptos-core
# RUN . $CARGO_HOME/env \
#     && cd aptos-core \
#     && cargo +nightly build --release -p aptos

# Expose the faucet port that's specified in the launch.json
EXPOSE 8081

# Set environment variables for better debugging (matching the launch.json debug configuration)
ENV RUST_BACKTRACE=1
ENV RUST_LOG_FORMAT=json


# Set the default command to run the experiments with default arguments
# Can be overridden by passing arguments to docker run
CMD ["/bin/bash"] 


# Run prototype experiments
# docker run your-image-name --runner prototype

# Run clean aptos experiments  
# docker run your-image-name --runner clean-aptos

# Run multi-worker experiments in multithreaded mode
# docker run your-image-name --runner multi-worker --mode multithreaded

# Run multi-worker experiments in single-threaded mode
# docker run your-image-name --runner multi-worker --mode single-threaded

# Run node in the background and write logs to file logs.txt > useful for experiment file generation
# nohup cargo run --release -p aptos -- node run-local-testnet --with-faucet --faucet-port 8081 --force-restart --assume-yes --evm-genesis-account 0x14Dcb427A216216791fB63973c5b13878de30916 > ../logs.txt 2>&1 &