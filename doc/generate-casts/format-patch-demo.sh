#!/usr/bin/env bash

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

# Copy example manifest
mkdir format-patch
pushd format-patch || exit 1

git init
cp -r ../update/* .
git config user.name "John Doe"
git config user.email "john.doe@example.com"
git add .
git commit -m "Initial commit"

sed -i 's/github/gitlab/g' cpputest/src/README.md
dfetch diff cpputest
mkdir -p patches
mv cpputest.patch patches/cpputest.patch

cat > dfetch.yaml <<'EOF'
manifest:
  version: 0.0

  remotes:
  - name: github
    url-base: https://github.com/

  projects:
  - name: cpputest
    dst: cpputest/src/
    repo-path: cpputest/cpputest.git
    tag: v3.4
    patch: patches/cpputest.patch

EOF


clear
# Run the command
pe "ls -l ."
pe "cat dfetch.yaml"
pe "cat patches/cpputest.patch"
pe "dfetch format-patch cpputest --output-directory formatted-patches"
pe "cat formatted-patches/cpputest.patch"


PROMPT_TIMEOUT=3
wait

pei ""

popd || exit 1
rm -rf format-patch
