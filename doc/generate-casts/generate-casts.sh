#!/bin/bash

# Uses relative paths
cd "$(dirname "$0")"

rm -rf ../asciicasts/*

asciinema rec --overwrite -c "./basic-demo.sh" ../asciicasts/basic.cast
asciinema rec --overwrite -c "./init-demo.sh" ../asciicasts/init.cast
asciinema rec --overwrite -c "./environment-demo.sh" ../asciicasts/environment.cast
asciinema rec --overwrite -c "./validate-demo.sh" ../asciicasts/validate.cast
asciinema rec --overwrite -c "./check-demo.sh" ../asciicasts/check.cast
asciinema rec --overwrite -c "./check-ci-demo.sh" ../asciicasts/check-ci.cast
asciinema rec --overwrite -c "./update-demo.sh" ../asciicasts/update.cast

# Depends on artifacts from update
asciinema rec --overwrite -c "./report-demo.sh" ../asciicasts/report.cast
asciinema rec --overwrite -c "./report-sbom-demo.sh" ../asciicasts/sbom.cast
asciinema rec --overwrite -c "./freeze-demo.sh" ../asciicasts/freeze.cast
asciinema rec --overwrite -c "./diff-demo.sh" ../asciicasts/diff.cast

rm -rf update

git clone --quiet --depth=1 --branch 3.0.0 https://github.com/jgeudens/ModbusScope.git 2> /dev/null
pushd ModbusScope
git submodule update --quiet --init > /dev/null
asciinema rec --overwrite -c "../import-demo.sh" ../../asciicasts/import.cast
popd
rm -rf ModbusScope

# Find all files with the .cast extension in the specified directory
files=$(find "../asciicasts" -type f -name '*.cast')

# Process each file
for file in $files; do
    ./strip-setup-from-cast.sh "${file}"
done
