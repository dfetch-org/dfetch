#!/usr/bin/env bash
# Demo of `dfetch replay-patches --interactive` across multiple projects.
#
# Drives the real multi-project tree TUI (Up/Down switch project, Left/Right
# step patches) through interactive_helper.py so the recording needs no
# human input.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/demo-magic/demo-magic.sh"

PROMPT_TIMEOUT=1

WORKDIR="$(mktemp -d "$DIR/replay-patches-multi.XXXXXX")"
trap 'popd 2>/dev/null; rm -rf "$WORKDIR"' EXIT
pushd "$WORKDIR" || { echo 'pushd failed' >&2; exit 1; }

git init
cp -r "$DIR/update"/* .
git add .
git commit -m "Initial commit"

sed -i 's/github/gitlab/g' cpputest/src/README.md
dfetch diff cpputest
sed -i 's/github/gitlab/g' jsmn/README.md
dfetch diff jsmn
mkdir -p patches
mv cpputest.patch patches/cpputest.patch
mv jsmn.patch patches/jsmn.patch

cat > dfetch.yaml <<'EOF'
manifest:
  version: 0.0

  remotes:
  - name: github
    url-base: https://github.com/

  projects:
  - name: cpputest
    dst: cpputest/src/
    repo-path: cpputest/cpputest.git
    tag: v3.4
    patch: patches/cpputest.patch

  - name: jsmn
    repo-path: zserge/jsmn.git
    branch: master
    patch: patches/jsmn.patch

EOF

dfetch update -f cpputest jsmn
git add .
git commit -m 'Fix vcs host'

clear
# Run the command
pe "cat dfetch.yaml"

# Step cpputest's one patch, switch focus to jsmn, step its one patch, then
# finish -- see doc/asciicasts/replay-patches-multi.cast for what this
# looks like.
KEYSTROKES=$(cat <<'KEYSTROKES'
WAIT "Ctrl-C abort" SEND RIGHT DELAY 0.9
WAIT "\[all/1 patches applied\]" SEND DOWN DELAY 0.9
WAIT "> jsmn" SEND RIGHT DELAY 0.9
WAIT "\[all/1 patches applied\]" SEND ENTER DELAY 0.9
KEYSTROKES
)

p "dfetch replay-patches --interactive cpputest jsmn"
echo "$KEYSTROKES" | python3 "$DIR/interactive_helper.py" replay-patches --interactive cpputest jsmn
status=$?

PROMPT_TIMEOUT=3
wait

pei ""

exit "$status"
