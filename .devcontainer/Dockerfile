FROM mcr.microsoft.com/devcontainers/python:3.13-trixie@sha256:c3a082525f51bb81e3d952d5ec12c2bed3525179a45ef3a09d48993ebc871133

# Install dependencies
# pv is required for asciicasts
RUN apt-get update && apt-get install --no-install-recommends -y \
    ccache=4.11.2-2 \
    pv=1.9.31-1 \
    patchelf=0.18.0-1.4 \
    subversion=1.14.5-3 && \
    rm -rf /var/lib/apt/lists/*

# Install ruby gem FPM for packaging
RUN apt-get update && apt-get install --no-install-recommends -y \
    ruby=1:3.3+b1 \
    ruby-dev=1:3.3+b1 \
    build-essential=12.12 \
    rpm=4.20.1+dfsg-3 \
    git=1:2.47.3-0+deb13u1 \
    curl=8.14.1-2+deb13u2 \
    ca-certificates=20250419 && \
    gem install --no-document fpm --version 1.17.0 && \
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
