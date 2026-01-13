#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest
mkdir update-patch
pushd update-patch

git init
cp -r ../update/* .
git add .
git commit -m "Initial commit"

pe "ls -l cpputest/src/README.md"
pe "sed -i 's/github/gitlab/g' cpputest/src/README.md"
pe "dfetch diff cpputest"
pe "mkdir -p patches"
pe "mv cpputest.patch patches/cpputest.patch"

# Insert patch @ line 13 (fragile if init manifest ever changes, but hoping for add command)
pe "sed -i '13i\    patch: patches/cpputest.patch' dfetch.yaml"
pe "dfetch update -f cpputest"
git commit -A -m 'Fix vcs host'

clear
# Run the command
pe "ls -l ."
pe "cat dfetch.yaml"
pe "cat patches/cpputest.patch"
pe "git status"
pe "sed -i 's/gitlab/gitea/g' cpputest/src/README.md"
pe "git add ."
pe "git commit -A -m 'Fix vcs host'"
pe "dfetch update-patch cpputest"
pe "cat patches/cpputest.patch"
pe "git status"


PROMPT_TIMEOUT=3
wait

pei ""

popd
rm -rf update-patch
