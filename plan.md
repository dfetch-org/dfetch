# Plan: Combined multi-project replay-patches

## Context

`replay-patches` currently processes projects one at a time, each with its own
pause/restore cycle. When a user wants to see several vendored patch stacks at
once (e.g. in VS Code's Changes view), they must review them sequentially.

The fix: when exactly one project resolves, keep the current per-project
behaviour unchanged. When two or more projects resolve:
- **Non-interactive** (default): validate all → fetch+stage all → apply per-project
  patch counts → single pause → restore all.
- **`--interactive`**: launch a combined tree TUI where the user steps each
  project's patch stack independently before pressing Enter to restore.

Per-project patch counts in non-interactive combined mode use an optional
`project:N` suffix on each project argument.

---

## CLI behaviour

```bash
# Single project — unchanged behaviour
dfetch replay-patches proj-a
dfetch replay-patches --count 2 proj-a
dfetch replay-patches --interactive proj-a

# Single project with :N shorthand (equivalent to --count N)
dfetch replay-patches proj-a:2

# Combined non-interactive (2+ projects, pause once)
dfetch replay-patches                          # all projects, all patches
dfetch replay-patches proj-a proj-b            # two projects, all patches
dfetch replay-patches proj-a:0 proj-b proj-c:1 # 0 / all / 1 patches

# Combined interactive tree TUI
dfetch replay-patches --interactive            # all projects, tree TUI
dfetch replay-patches --interactive proj-a proj-b
```

**Rejected combinations** (raise `RuntimeError`):
- `--count` with 2+ projects → `"--count is for single-project use; use project:N syntax for per-project counts"`
- `--count` and `:N` suffix on same project → `"use either --count or project:N, not both"`

---

## Parsing `project:N` syntax

Add a helper at module level:

```python
def _parse_project_spec(spec: str) -> tuple[str, int | None]:
    """Split 'name:N' into (name, N); bare name returns (name, None)."""
    if ":" in spec:
        name, _, tail = spec.rpartition(":")
        try:
            return name, int(tail)
        except ValueError:
            raise RuntimeError(
                f"invalid project spec {spec!r}; expected name or name:N"
            )
    return spec, None
```

---

## Dispatch in `__call__`

```python
# Parse project:N specs
parsed = [_parse_project_spec(s) for s in args.projects]
project_names = [name for name, _ in parsed]
per_project_counts: dict[str, int] = {
    name: n for name, n in parsed if n is not None
}

# Reject --count + :N on the same project
if args.count is not None:
    overlap = [n for n in per_project_counts if n in project_names]
    if overlap:
        raise RuntimeError(f"use either --count or project:N, not both (conflicts: {overlap})")

selected = list(superproject.manifest.selected_projects(project_names))

if len(selected) <= 1:
    count = args.count
    if count is None and selected and selected[0].name in per_project_counts:
        count = per_project_counts[selected[0].name]
    self._iter_projects(superproject, project_names,
        lambda project: self._review_project(superproject, project, count, args.interactive))
else:
    if args.count is not None:
        raise RuntimeError("--count is for single-project use; use project:N syntax for per-project counts")
    with in_directory(superproject.root_directory):
        _review_projects_combined(superproject, selected, per_project_counts, args.interactive)
```

Add `from dfetch.util.util import in_directory` to imports.

---

## `_ProjectState` dataclass

```python
@dataclasses.dataclass
class _ProjectState:
    name: str
    local_path: str
    patches: list[str]
    current: int = 0

    @property
    def fully_patched(self) -> bool:
        return self.current == len(self.patches)
```

---

## `_review_projects_combined`

1. **Validate** — `_can_review_project` for each; collect `reviewable`.
2. **Fetch + stage all** — `update(patch_count=0)` + `add_path` per project; append to `staged`.
3. **Apply / review**:
   - `interactive=True`: `_step_tui_multi(states)` (TUI drives apply/unapply)
   - `interactive=False`: `apply_patches(per_project_counts.get(name, -1))` per project, log, `input("Press Enter to restore...")` if TTY
4. **Restore all** in `finally`: loop `staged`, call `_restore_project(..., state.fully_patched, ...)`, restore metadata bytes.

---

## Combined interactive tree TUI

### Layout

```
  ← → step    ↑ ↓ switch project    Enter restore and exit    Ctrl-C abort
  ─────────────────────────────────────────────────────────────────────────
  proj-a  [2/3 patches applied]
    [x] patches/00-fix.patch
    [x] patches/01-improve.patch
    [ ] patches/02-final.patch
> proj-b  [0/2 patches applied]
    [ ] patches/00-base.patch
    [ ] patches/01-extra.patch
```

### `_step_tui_multi(states)`

- `UP` / `DOWN`: move `focused` index between projects
- `LEFT` / `RIGHT` / `ENTER` / `ESC`: delegate to existing `_apply_step` with focused project's state
- `Ctrl-C`: `screen.clear(); return`

---

## Files to change

| File | Change |
|------|--------|
| `dfetch/commands/replay_patches.py` | Add `dataclasses` + `in_directory` imports; `_ProjectState`; `_parse_project_spec`; modify `__call__`; add `_review_projects_combined`, `_draw_tui_tree`, `_step_tui_multi` |
| `tests/test_replay_patches.py` | Unit tests for combined path |
| `features/replay-patches-in-git.feature` | BDD scenario: combined non-interactive pass |
| `doc/howto/patching.rst` | Document automatic combined mode + `project:N` syntax |
| `CHANGELOG.rst` | One bullet |

---

## New unit tests

- `test_combined_two_projects_all_patches`: `add_path` × 2, `apply_patches(-1)` × 2, `restore_staged` × 2
- `test_combined_per_project_counts`: counts 0/−1/1, verify correct `apply_patches` args and restore strategies
- `test_combined_count_flag_raises`: `--count 1` + 2 projects → RuntimeError
- `test_combined_count_and_suffix_raises`: `--count 1 proj:2` → RuntimeError
- `test_single_project_suffix_becomes_count`: `proj:2` alone → `_review_project` with `count=2`
- `test_combined_interactive_launches_tui`: `--interactive` + 2 projects → `_step_tui_multi` called
