#!/usr/bin/env bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/demo-magic/demo-magic.sh"

PROMPT_TIMEOUT=1

WORKDIR="$(mktemp -d "$DIR/update-patch-intermediate.XXXXXX")"
trap 'popd 2>/dev/null; rm -rf "$WORKDIR"' EXIT

# A tiny "upstream" remote to vendor, with three well-separated concerns to
# fix up: a namespace, a logging backend, and a local build-mode tweak. The
# sections are spaced out so each patch's context stays within its own
# section, the same way patches in a real, larger file would.
mkdir -p "$WORKDIR/remote"
pushd "$WORKDIR/remote" || { echo 'pushd failed' >&2; exit 1; }
git init --quiet --initial-branch=master
git config user.email you@example.com
git config user.name "Upstream"
git config commit.gpgsign false
cat > config.h <<'EOF'
// Namespace used for all exported symbols in this library.
#define NAMESPACE upstream

// -----------------------------------------------------------------------
// Logging
// -----------------------------------------------------------------------
// Backend used to emit log messages.
#define LOG_BACKEND stdout

// -----------------------------------------------------------------------
// Build
// -----------------------------------------------------------------------
// Build mode selected for this vendored copy.
#define BUILD_MODE release
EOF
git add -A && git commit --quiet -m "Initial commit"
git tag -a v1 -m "v1"
popd || exit 1

mkdir -p "$WORKDIR/project"
pushd "$WORKDIR/project" || { echo 'pushd failed' >&2; exit 1; }
git init --quiet --initial-branch=master
git config user.email you@example.com
git config user.name "John Doe"
git config commit.gpgsign false

mkdir -p patches
cat > dfetch.yaml <<EOF
manifest:
  version: 0.0
  projects:
  - name: mylib
    url: file://$WORKDIR/remote
    dst: mylib
EOF
dfetch update mylib > /dev/null
git add -A && git commit --quiet -m "Initial commit"

# Patch 1: adapt the namespace to our project.
sed -i 's/NAMESPACE upstream/NAMESPACE ourproject/' mylib/config.h
dfetch diff mylib > /dev/null
mv mylib.patch patches/0001-rename-namespace.patch
sed -i '/dst: mylib/a\    patch: patches/0001-rename-namespace.patch' dfetch.yaml
dfetch update -f mylib > /dev/null
git add -A && git commit --quiet -m "Add patch 1"

# Patch 2: swap the logging backend, and default it to info-level logging.
sed -i -e 's/LOG_BACKEND stdout/LOG_BACKEND syslog/' \
       -e '/LOG_BACKEND syslog/a #define DEFAULT_LOG_LEVEL "info"' mylib/config.h
dfetch diff mylib > /dev/null
mv mylib.patch patches/0002-swap-logging-backend.patch
sed -i 's#patch: patches/0001-rename-namespace.patch#patch:\n      - patches/0001-rename-namespace.patch\n      - patches/0002-swap-logging-backend.patch#' dfetch.yaml
dfetch update -f mylib > /dev/null
git add -A && git commit --quiet -m "Add patch 2"

# Patch 3: an unrelated, small project-specific tweak.
sed -i 's/BUILD_MODE release/BUILD_MODE local/' mylib/config.h
dfetch diff mylib > /dev/null
mv mylib.patch patches/0003-local-project-overlay.patch
sed -i 's#- patches/0002-swap-logging-backend.patch#- patches/0002-swap-logging-backend.patch\n      - patches/0003-local-project-overlay.patch#' dfetch.yaml
dfetch update -f mylib > /dev/null
git add -A && git commit --quiet -m "Add patch 3"

clear
# Run the command
pe "sed 's#url: file://.*#url: some-remote-server/mylib.git#' dfetch.yaml"
pe "cat patches/0002-swap-logging-backend.patch"
pe "sed -i 's/DEFAULT_LOG_LEVEL \"info\"/DEFAULT_LOG_LEVEL \"debug\"/' mylib/config.h"
pe "git commit -am 'Enable debug logging'"
pe "dfetch update-patch mylib --patch 0002-swap-logging-backend"
pe "cat patches/0002-swap-logging-backend.patch"
pe "git status"

PROMPT_TIMEOUT=3
wait

pei ""

popd || exit 1
