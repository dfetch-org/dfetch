# Generate casts

This folder makes it possible to generate asciinema casts.
The solution was completely inspired by https://stackoverflow.com/a/63080929/1149326
It can only run on linux.

## Requirements

```console
pip install -e .[casts]
```

`interactive_add_helper.py` drives `dfetch add -i`'s real tree-browser UI
through its own pty (via `pexpect`), so the recording needs no human input.

## Usage
```console
./generate-casts.sh
```
