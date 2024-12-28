FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

# Install dependencies
# pv is required for asciicasts
RUN apt-get update && apt-get install -y \
    pv \
    subversion \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspaces/dfetch

COPY . .

RUN pip install --no-cache-dir --root-user-action=ignore --upgrade pip && \
    pip install --no-cache-dir --root-user-action=ignore -e .[development,docs,test,casts] && \
    pre-commit install --install-hooks

# Add a non-root user (dev)
RUN useradd -m dev && chown -R dev:dev /workspaces/dfetch
USER dev

# Set bash as the default shell
SHELL ["/bin/bash", "-ec"]
