#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest
mkdir init
pushd init

clear

# Run the command
pe "ls -l"
pe "dfetch init"
pe "ls -l"
pe "cat dfetch.yaml"

PROMPT_TIMEOUT=3
wait

pei ""

popd
rm -rf init
