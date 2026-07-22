#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest
mkdir review-patch
pushd review-patch || exit 1

git init
cp -r ../update/* .
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
# Pipe stdin to avoid blocking on "Press Enter to restore..."
pe "echo '' | dfetch replay-patches cpputest"

PROMPT_TIMEOUT=3
wait

pei ""

popd || exit 1
rm -rf review-patch
