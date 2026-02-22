#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest
mkdir add
pushd add
dfetch init
clear

# Run the command
pe "cat dfetch.yaml"
pe "dfetch add -f https://github.com/dfetch-org/dfetch.git"
pe "cat dfetch.yaml"

PROMPT_TIMEOUT=3
wait

pei ""

popd
rm -rf add
