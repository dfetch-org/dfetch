#!/usr/bin/env bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/demo-magic/demo-magic.sh"

PROMPT_TIMEOUT=1

WORKDIR="$(mktemp -d "$DIR/review-patch.XXXXXX")"
trap 'popd 2>/dev/null; rm -rf "$WORKDIR"' EXIT
pushd "$WORKDIR" || { echo 'pushd failed' >&2; exit 1; }

git init
cp -r "$DIR/update"/* .
git add .
git commit -m "Initial commit"

sed -i 's/github/gitlab/g' cpputest/src/README.md
dfetch diff cpputest
mkdir -p patches
mv cpputest.patch patches/cpputest.patch

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

EOF

dfetch update -f cpputest
git add .
git commit -m 'Fix vcs host'

clear
# Run the command
pe "cat dfetch.yaml"
pe "cat patches/cpputest.patch"
# Show the command a user would actually type; feed it empty stdin behind
# the scenes so recording doesn't block on "Press Enter to restore..."
p "dfetch replay-patches cpputest"
echo '' | dfetch replay-patches cpputest
status=$?

PROMPT_TIMEOUT=3
wait

pei ""

exit "$status"
