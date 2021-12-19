#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest
mkdir freeze
pushd freeze

cp -r ../update/* .
clear

# Run the command
pe "cat dfetch.yaml"
pe "dfetch freeze"
pe "cat dfetch.yaml"
pe "ls -l ."


PROMPT_TIMEOUT=3
wait

pei ""

popd
rm -rf freeze
