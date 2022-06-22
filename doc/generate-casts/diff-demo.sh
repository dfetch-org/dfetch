#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest
mkdir diff
pushd diff

git init
cp -r ../update/* .
git add .
git commit -m "Initial commit"
clear

# Run the command
pe "ls -l ."
pe "ls -l cpputest/src/README.md"
pe "sed -i 's/github/gitlab/g' cpputest/src/README.md"
pe "dfetch diff cpputest"
pe "cat cpputest.patch"


PROMPT_TIMEOUT=3
wait

pei ""

popd
rm -rf diff
