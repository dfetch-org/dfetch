FROM mcr.microsoft.com/devcontainers/python:3.13-bullseye@sha256:c013106c845c52c9bae1271180882bcc5684c0fc65e3164d43cac5ec85ee1922

# Install dependencies
# pv is required for asciicasts
RUN apt-get update && apt-get install --no-install-recommends -y \
    ccache=4.2-1 \
    pv=1.6.6-1+b1 \
    patchelf=0.12-1 \
    subversion=1.14.1-3+deb11u2 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspaces/dfetch

# Add a non-root user (dev)
RUN useradd -m dev && chown -R dev:dev /workspaces/dfetch

USER dev

ENV PATH="/home/dev/.local/bin:${PATH}"
ENV PYTHONPATH="/home/dev/.local/lib/python3.12"
ENV PYTHONUSERBASE="/home/dev/.local"

COPY --chown=dev:dev . .

RUN pip install --no-cache-dir --root-user-action=ignore --upgrade pip==25.2 \
    && pip install --no-cache-dir --root-user-action=ignore -e .[development,docs,test,casts,build] \
    && pre-commit install --install-hooks

# Set bash as the default shell
SHELL ["/bin/bash", "-ec"]
