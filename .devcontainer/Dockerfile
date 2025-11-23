FROM mcr.microsoft.com/devcontainers/python:3.13-bullseye@sha256:735ecc489de65d36b6ac4e8e5e37287cb30711bac0dd292770bf5347228c438e

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
ENV PYTHONPATH="/home/dev/.local/lib/python3.13"
ENV PYTHONUSERBASE="/home/dev/.local"

COPY --chown=dev:dev . .

RUN pip install --no-cache-dir --root-user-action=ignore --upgrade pip==25.3 \
    && pip install --no-cache-dir --root-user-action=ignore -e .[development,docs,test,casts,build] \
    && pre-commit install --install-hooks

# Set bash as the default shell
SHELL ["/bin/bash", "-ec"]
