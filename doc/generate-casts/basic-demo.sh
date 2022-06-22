#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest
mkdir basic
pushd basic

dfetch init
clear

# Run the command
pe "ls -l"
pe "cat dfetch.yaml"
pe "dfetch check"
pe "sed -i 's/v3.4/v4.0/g' dfetch.yaml"
pe "cat dfetch.yaml"
pe "dfetch update"
pe "ls -l"

PROMPT_TIMEOUT=3
wait

pei ""

popd
rm -rf basic
