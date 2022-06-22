#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest
mkdir check
pushd check

dfetch init
clear

# Run the command
pe "cat dfetch.yaml"
pe "dfetch check"

PROMPT_TIMEOUT=3
wait

pei ""

popd
rm -rf check
