#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest
mkdir validate
pushd validate

dfetch init
clear

# Run the command
pe "dfetch validate"

PROMPT_TIMEOUT=3
wait

popd
rm -rf validate
