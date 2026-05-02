# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## What is dfetch

dfetch is a Python vendoring tool that fetches external dependencies (from Git, SVN, or archive files) and copies them directly into a project as plain files — no submodules, no externals. Dependencies are declared in a YAML manifest file.

## Commands

### Running tests

```bash
# Unit tests (pytest)
pytest tests/

# Single unit test
pytest tests/test_manifest.py::test_name

# BDD feature tests (behave)
behave features/

# Single feature file
behave features/git-fetch.feature

# Feature tests for a specific command (e.g. update, check, diff, report)
behave features/ --tags=update

# Full test run with coverage (as CI does it)
pytest --cov=dfetch tests/
coverage run --source=dfetch --append -m behave features
coverage xml -o coverage.xml
```

### Linting and type checking

```bash
black --check dfetch          # formatting
isort --diff dfetch           # import ordering
pylint dfetch                 # PEP8 / style
ruff check dfetch             # fast linter
mypy dfetch                   # type checking
pyright .                     # additional type checking
pydocstyle dfetch             # docstring style (Google convention)
bandit -r dfetch              # security checks
lint-imports                  # architecture layer enforcement (see below)
```

### Installation

```bash
pip install -e .[development,test]
```

## Architecture

The architecture follows a **strict layered C4 model** enforced by `lint-imports`. Dependencies between layers are **unidirectional** — lower layers cannot import from higher ones. Violating this will fail CI.

```
dfetch.commands     ← top layer (CLI commands, user-facing)
dfetch.reporting    ← report generation
dfetch.project      ← project/dependency abstraction
dfetch.manifest     ← YAML manifest parsing (independent)
dfetch.vcs          ← VCS backends: Git, SVN, Archive (independent)
dfetch.util         ← shared utilities (independent)
dfetch.log          ← logging (lowest layer)
```

### Key modules

- **`dfetch/__main__.py`** — CLI entry point; builds argparse subcommands and dispatches
- **`dfetch/commands/`** — One file per CLI command (e.g., `update.py`, `check.py`); all inherit from `command.py`'s abstract `Command` base
- **`dfetch/manifest/`** — YAML manifest loading/writing with `strictyaml` schema validation; `manifest.py` is the main handler
- **`dfetch/project/`** — Abstract `Subproject`/`Superproject` classes with concrete Git, SVN, and Archive implementations; factory functions `create_sub_project()` and `create_super_project()` are the main entry points
- **`dfetch/vcs/`** — Low-level VCS operations: `git.py`, `svn.py`, `archive.py` (with hash verification in `integrity_hash.py`), and `patch.py`
- **`dfetch/reporting/`** — Output formatters; check results can be emitted as stdout, Jenkins JSON, SARIF, or Code Climate format; SBOM output uses CycloneDX format
- **`dfetch/terminal/`** — Terminal UI components (interactive prompts, tree browser, ANSI colors)

### Adding a new command

1. Create `dfetch/commands/<name>.py` implementing the `Command` ABC
2. Register it in `dfetch/__main__.py`
3. Respect layer boundaries: commands may import from `reporting`, `project`, `manifest`, `vcs`, `util`, `log` — but not vice versa

### Adding a new VCS backend

Implement the abstract interfaces in `dfetch/project/subproject.py` and `dfetch/vcs/` and register via the factory in `dfetch/project/`.

## Testing conventions

- **Unit tests** live in `tests/` and use `pytest`. Test files mirror module names (e.g., `tests/test_manifest.py`).
- **BDD feature tests** live in `features/` and use `behave`. Step definitions are in `features/steps/`. Feature files describe end-to-end workflows.
- Feature files are tagged with the command they exercise (e.g. `@update`, `@check`). If your change affects a command, run its feature tests using the command tag: `behave features/ --tags=<command>`.
- Docstrings in test functions follow Google style as a convention (CI runs `pydocstyle dfetch` and does not check `tests/`, so this is not enforced automatically).

## Code quality rules

- **Cyclomatic complexity** must stay below 8 per function. If a function grows beyond this, refactor it — extract helpers, simplify conditionals, or split responsibilities.
- **No lint suppressions without fixing the root cause.** Avoid `# noqa`, `# type: ignore`, `# pylint: disable`, `# pyright: ignore`, and similar inline suppressions. If a tool flags something, fix it properly rather than silencing it. The one accepted exception is module-level tool headers at the top of test files (e.g. `# mypy: ignore-errors` or `# flake8: noqa` on line 1–5 of a test module); these are permitted where the test file structure genuinely prevents a clean fix.

## Security model

`security/threat_model.py` is an executable pytm model that must stay aligned with `doc/explanation/security.rst`.

After any change that could affect the security posture — including but not limited to:

- Adding, removing, or renaming a CLI command, VCS backend, or data flow
- Changing how manifests, credentials, archives, or patches are handled
- Modifying GitHub Actions workflows or the PyPI publish pipeline
- Adding or removing external dependencies or subprocess calls

— review both files and update them as needed:

1. **`security/threat_model.py`** — add, remove, or update the relevant `Process`, `ExternalEntity`, `Datastore`, `Data`, or `Dataflow` objects and their `controls.*` annotations.
2. **`doc/explanation/security.rst`** — keep the asset register (PA/SA/EA tables), data-flow table, controls table, and known-gaps section consistent with the model.

You can verify the model is syntactically valid by running:

```bash
python -m security.threat_model --report
```

(requires `pip install .[docs]`; diagram commands additionally require PlantUML and Graphviz)

## Documentation

Every change must be reflected in the documentation. Depending on the nature of the change:

- **User-visible behaviour** (new feature, changed CLI, new option) → update the relevant `doc/how-to/` or `doc/reference/` page
- **Notable fix or change** → add an entry to the changelog (`doc/changelog/`)
- **Architecture change** → update `doc/explanation/architecture.rst`

Documentation lives in `doc/` and is built with Sphinx.

### Tone of voice

Write documentation that is helpful, supportive, and positive. Assume the reader is capable — guide them forward rather than warning them away. Prefer "you can" over "you must", favour concrete examples over abstract rules, and end explanations on what the user can now do rather than what might go wrong.
