# DFetch add workflow

Add a new project to `dfetch.yaml` and fetch it.

The user may pass a URL or description as `$ARGUMENTS`. If they did not, ask for the URL before proceeding.

## Step 1 — Read the manifest

Read `dfetch.yaml` to understand the existing remotes and project patterns.

## Step 2 — Classify the URL

Determine the VCS type from the URL:

- **archive** — URL ends in `.zip`, `.tar.gz`, `.tar.bz2`, `.tar.xz`, or similar.
- **svn** — URL contains `svn`, uses `svn+ssh://`, or the user says so.
- **git** — everything else.

## Step 3 — Gather details

`dfetch add` auto-detects the default branch and guesses a destination, so you only need to ask about things it cannot infer. Use `AskUserQuestion` to collect what you don't yet know:

**For git and SVN:**

Only ask what the user hasn't already told you:
- **Name** — defaults to the repo name from the URL; confirm or let the user override.
- **Destination** (`dst`) — where in the repo the files should land; `dfetch add` guesses from existing project paths, but ask if the user has a preference.
- **Version** — branch, tag, or revision to pin. Leave blank to track the default branch.
- **Source path** (`src`) — sub-path or glob inside the remote repo (e.g. `lib/` or `*.h`). Leave blank to copy everything.
- **Ignore patterns** — glob patterns to exclude. Leave blank for none.

**For archives, also ask:**
- **Source path** (`src`) — sub-directory inside the archive to copy (archives often have a single wrapping top-level directory that dfetch strips automatically).
- **Ignore patterns** — globs to filter out unwanted files (other font families, binary formats, etc.).
- **Integrity hash** — whether to verify the download (strongly recommended; you will compute it).

## Step 4 — Add the project

**Git and SVN** — use the CLI, which appends the entry to `dfetch.yaml` and records the resolved remote:

```bash
dfetch add --name <name> --dst <dst> [--src <src>] [--version <version>] \
           [--ignore <p1> <p2> ...] <url>
```

Omit flags for fields the user left blank; `dfetch add` will fill in sensible defaults.

**Archives** — edit `dfetch.yaml` directly with the Edit tool. The CLI does not support `vcs: archive`, `integrity:`, or archive-specific `src` paths. Follow the style of existing archive entries:

```yaml
- name: <name>
  remote: <remote>          # use an existing remote if its url-base is a prefix of the URL; omit otherwise
  vcs: archive
  src: <path-in-archive>    # omit if copying from the archive root
  dst: <dst>
  repo-path: <url-or-path>
  ignore:
    - <pattern>
  integrity:
    hash: sha256:<hash>
```

Compute the hash before writing the entry:

```bash
curl -sL <url> | sha256sum
```

When reusing an existing remote, `repo-path` is the URL suffix after the remote's `url-base`. When no remote matches, omit `remote:` and use the full URL as `repo-path`.

## Step 5 — Fetch and verify

Run `dfetch update <name>`. If it fails:

| Error | Fix |
|---|---|
| `src … not found in archive` | Inspect the archive with `unzip -l <file>` or `tar -tf <file>`. If the archive has a single top-level wrapper directory, dfetch strips it — adjust `src` accordingly. |
| Integrity mismatch | Recompute the hash and update the `integrity` field. |
| Remote not found | Check that `remote:` matches a name in the `remotes:` list. |
| Branch/tag not found | Run `dfetch add -i <url>` in a terminal to browse available versions interactively, then copy the chosen value back into the manifest. |

## Step 6 — Confirm

Show the user the new entry that was added to `dfetch.yaml` and list the files that were fetched to `dst`.
