#!/usr/bin/env bash

source ../demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

clear

# Run the command
pe "ls -l"
pe "cat .gitmodules"
pe "dfetch import"
pe "cat dfetch.yaml"

PROMPT_TIMEOUT=3
wait

pei ""
