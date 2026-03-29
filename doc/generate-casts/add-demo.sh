#!/usr/bin/env bash
set -euo pipefail

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest
mkdir add
pushd add || { echo 'pushd failed' >&2; exit 1; }
dfetch init
clear

# Run the command
pe "cat dfetch.yaml"
pe "dfetch add https://github.com/dfetch-org/dfetch.git"
pe "cat dfetch.yaml"

PROMPT_TIMEOUT=3
wait

pei ""

popd || { echo 'popd failed' >&2; exit 1; }
rm -rf add
