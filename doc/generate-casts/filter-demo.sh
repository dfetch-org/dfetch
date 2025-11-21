#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest
mkdir filter
pushd filter

cp -r ../update/* .
clear

# Run the command
pe "cat dfetch.yaml"
pe "dfetch filter"
pe "find . | dfetch filter"
pe "find . | dfetch filter echo"


PROMPT_TIMEOUT=3
wait

pei ""

popd
rm -rf filter
