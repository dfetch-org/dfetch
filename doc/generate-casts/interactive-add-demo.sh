#!/usr/bin/env bash
# Demo of dfetch add -i (interactive wizard mode).
#
# Uses the real cpputest repository so the viewer sees dfetch fetching live
# branch/tag metadata and the wizard populating from it.

source ./demo-magic/demo-magic.sh

PROMPT_TIMEOUT=1

mkdir interactive-add
pushd interactive-add

# Start with a manifest that already has one dependency so the demo shows
# adding to an existing project rather than starting from scratch.
cat > dfetch.yaml << 'MANIFEST'
manifest:
  version: '0.0'
  projects:
  - name: jsmn
    url: https://github.com/zserge/jsmn.git
    branch: master
MANIFEST

clear

pe "cat dfetch.yaml"

p "dfetch add -i https://github.com/cpputest/cpputest.git"
python3 ../interactive_add_helper.py https://github.com/cpputest/cpputest.git

pe "cat dfetch.yaml"

PROMPT_TIMEOUT=3
wait

pei ""

popd
rm -rf interactive-add
