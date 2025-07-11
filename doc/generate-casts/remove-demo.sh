#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest and fetch projects
mkdir remove
pushd remove

dfetch init
dfetch update
clear

# Run the command
pe "cat dfetch.yaml"
pe "ls -la cpputest/src"
pe "dfetch remove cpputest"
pe "cat dfetch.yaml"
pe "ls -la cpputest"

PROMPT_TIMEOUT=3
wait

pei ""

popd
rm -rf remove
