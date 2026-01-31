#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest
mkdir update-patch
pushd update-patch || exit 1

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
pe "ls -l ."
pe "cat dfetch.yaml"
pe "cat patches/cpputest.patch"
pe "git status"
pe "sed -i 's/gitlab/gitea/g' cpputest/src/README.md"
pe "git add ."
pe "git commit -a -m 'Fix vcs host'"
pe "dfetch update-patch cpputest"
pe "cat patches/cpputest.patch"
pe "git status"


PROMPT_TIMEOUT=3
wait

pei ""

popd || exit 1
rm -rf update-patch
