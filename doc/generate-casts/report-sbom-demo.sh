#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest
mkdir report_sbom
pushd report_sbom

cp -r ../update/* .
clear

# Run the command
pe "ls -l"
pe "dfetch report -t sbom"
pe "cat report.json"


PROMPT_TIMEOUT=3
wait

popd
rm -rf report_sbom
