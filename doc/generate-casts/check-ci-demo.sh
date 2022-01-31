#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest
mkdir check_ci
pushd check_ci

dfetch init
clear

# Run the command
pe "cat dfetch.yaml"
pe "dfetch check --jenkins-json jenkins.json --sarif sarif.json"
pe "ls -l ."
pe "cat jenkins.json"
pe "cat sarif.json"

PROMPT_TIMEOUT=3
wait

pei ""

popd
rm -rf check_ci
