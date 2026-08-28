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
no human input. It has no knowledge of any specific dfetch command: it takes
the dfetch subcommand and arguments to run (e.g. `add --interactive <url>`)
as its own arguments, and reads a keystroke script from stdin (see the
module docstring for the format, and `interactive-add-demo.sh` for an
example) -- so each demo script owns the choices it wants to show off.

## Usage
```console
./generate-casts.sh
```
