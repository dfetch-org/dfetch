#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Remove any existing manifest
clear

# Run the command
pe "dfetch environment"

PROMPT_TIMEOUT=3
wait

pei ""
