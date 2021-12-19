#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest
mkdir update
pushd update

dfetch init
clear

# Run the command
pe "ls -l"
pe "cat dfetch.yaml"
pe "dfetch update"
pe "ls -l"
pe "dfetch update"

PROMPT_TIMEOUT=3
wait

popd
