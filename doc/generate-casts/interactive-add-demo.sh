#!/usr/bin/env bash
# Demo of dfetch add -i (interactive wizard mode).
#
# Uses the real cpputest repository so the viewer sees dfetch fetching live
# branch/tag metadata and the wizard populating from it.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/demo-magic/demo-magic.sh"

PROMPT_TIMEOUT=1

mkdir interactive-add
trap 'popd 2>/dev/null; rm -rf interactive-add' EXIT
pushd interactive-add || { echo 'pushd failed' >&2; exit 1; }

# Start with a manifest that already has one dependency so the demo shows
# adding to an existing project rather than starting from scratch.
cat > dfetch.yaml << 'MANIFEST'
manifest:
  version: '0.0'
  projects:
  - name: jsmn
    url: https://github.com/zserge/jsmn.git
    branch: master
MANIFEST

clear

pe "cat dfetch.yaml"

# Accept the default name/destination, pick the v3.4 tag, keep the whole
# repository as src, and ignore examples/ and tests/ -- see
# doc/asciicasts/interactive-add.cast for what this looks like.
KEYSTROKES=$(cat <<'KEYSTROKES'
WAIT "Name:" SEND ENTER DELAY 1.3
WAIT "Destination:" SEND ENTER DELAY 1.3
WAIT "Enter select" SEND DOWN DELAY 0.35 REPEAT 7
# Confirm the tag actually highlighted is v3.4 before pressing Enter --
# cpputest's branch/tag order could change upstream, and a fixed count of
# Down-presses would otherwise silently lock in whatever ended up there.
WAIT "▶.*v3\.4" SEND ENTER DELAY 0.9
WAIT "Esc skip" SEND ENTER DELAY 1.8
WAIT "Space toggle" SEND DOWN DELAY 0.35 REPEAT 5
WAIT "▶.*examples" SEND SPACE DELAY 0.35
SEND DOWN DELAY 0.35 REPEAT 7
WAIT "▶.*tests" SEND SPACE DELAY 0.35
SEND ENTER DELAY 0.9
WAIT "Add project to manifest?" SEND "y\r" DELAY 1.3
WAIT "Run '.*' now\?" SEND "n\r" DELAY 1.3
KEYSTROKES
)

p "dfetch add -i https://github.com/cpputest/cpputest.git"
echo "$KEYSTROKES" | python3 ../interactive_helper.py add --interactive https://github.com/cpputest/cpputest.git

pe "cat dfetch.yaml"

PROMPT_TIMEOUT=3
wait

pei ""

popd || { echo 'popd failed' >&2; exit 1; }
rm -rf interactive-add
