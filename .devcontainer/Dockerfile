FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

# Install dependencies
# pv is required for asciicasts
RUN apt-get update && apt-get install --no-install-recommends -y \
    pv=1.6.6-1+b1 \
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

RUN pip install --no-cache-dir --root-user-action=ignore --upgrade pip==25.1.1 \
    && pip install --no-cache-dir --root-user-action=ignore -e .[development,docs,test,casts] \
    && pre-commit install --install-hooks

# Set bash as the default shell
SHELL ["/bin/bash", "-ec"]
