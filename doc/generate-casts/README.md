# Generate casts

This folder makes it possible to generate asciinema casts.
The solution was completely inspired by https://stackoverflow.com/a/63080929/1149326
It can only run on linux.

## Requirements

```console
pip install -e .[casts]
```

`interactive_helper.py` drives an interactive dfetch command's real
tree-browser UI through its own pty (via `pexpect`), so the recording needs
no human input. It takes the dfetch subcommand and arguments to run (e.g.
`add --interactive <url>`) and looks up the scripted keystrokes for that
subcommand -- see `INTERACTIVE_ADD_KEYSTROKES` for `add -i`'s.

## Usage
```console
./generate-casts.sh
```
