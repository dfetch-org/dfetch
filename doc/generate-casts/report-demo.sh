#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest
mkdir report
pushd report

cp -r ../update/* .
clear

# Run the command
pe "ls -l"
pe "dfetch report"

PROMPT_TIMEOUT=3
wait

popd
rm -rf report
