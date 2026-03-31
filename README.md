![](doc/images/dfetch_header.png)
[![](https://codescene.io/projects/10989/status-badges/code-health)](https://codescene.io/projects/10989)
[![](https://codescene.io/projects/10989/status-badges/system-mastery)](https://codescene.io/projects/10989)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/431474d43db0420a92ebc10c1886df8d)](https://app.codacy.com/gh/dfetch-org/dfetch?utm_source=github.com&utm_medium=referral&utm_content=dfetch-org/dfetch&utm_campaign=Badge_Grade)
[![Codacy Badge](https://app.codacy.com/project/badge/Coverage/503c21c8e46b4baca0b4519bcc9fd51e)](https://www.codacy.com/gh/dfetch-org/dfetch/dashboard?utm_source=github.com&utm_medium=referral&utm_content=dfetch-org/dfetch&utm_campaign=Badge_Coverage)
[![Documentation Status](https://readthedocs.org/projects/dfetch/badge/?version=latest)](https://dfetch.readthedocs.io/en/latest/?badge=latest)
[![Build](https://github.com/dfetch-org/dfetch/workflows/Test/badge.svg)](https://github.com/dfetch-org/dfetch/actions)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GitHub](https://img.shields.io/github/license/dfetch-org/dfetch)](https://github.com/dfetch-org/dfetch/blob/main/LICENSE)
[![Gitter](https://badges.gitter.im/dfetch-org/community.svg)](https://gitter.im/dfetch-org/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)
[![Libraries.io dependency status for GitHub repo](https://img.shields.io/librariesio/github/dfetch-org/dfetch)](https://libraries.io/github/dfetch-org/dfetch)
![Maintenance](https://img.shields.io/maintenance/yes/2026)
[![GitHub issues](https://img.shields.io/github/issues/dfetch-org/dfetch)](https://github.com/dfetch-org/dfetch/issues)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/dfetch)
[![PyPI](https://img.shields.io/pypi/v/dfetch)](https://pypi.org/project/dfetch/)
[![Contribute with Codespaces](https://img.shields.io/static/v1?label=Codespaces&message=Open&color=blue)](https://codespaces.new/dfetch-org/dfetch)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/11245/badge)](https://www.bestpractices.dev/projects/11245)


**Vendor dependencies without the pain.**

**Dfetch** copies source code directly into your project — no Git submodules, no SVN externals,
no hidden external links. Fetch from Git, SVN, or plain archive URLs. Dependencies live as plain,
readable files inside your own repository. You stay in full control of every line.

Dfetch supports **Git**, **SVN**, and **archive files** (`.tar.gz`, `.tgz`, `.tar.bz2`, `.tar.xz`, `.zip`).
Archives can be verified with a cryptographic hash (`sha256`, `sha384`, or `sha512`) to guarantee
integrity on every fetch. No proprietary formats, no lock-in — switch tools any time.

Other tools that do similar things are Zephyr's West, CMake ExternalProject, and other meta tools.
See [alternatives](https://dfetch.readthedocs.io/en/latest/explanation/alternatives.html) for a complete list.
The broader concept is known as [*vendoring*](https://dfetch.readthedocs.io/en/latest/explanation/vendoring.html).

[**Getting started**](https://dfetch.readthedocs.io/en/latest/tutorial/getting_started.html) |
[**Commands**](https://dfetch.readthedocs.io/en/latest/reference/commands.html) |
[**Troubleshooting**](https://dfetch.readthedocs.io/en/latest/howto/troubleshooting.html)  |
[**Contributing**](https://dfetch.readthedocs.io/en/latest/howto/contributing.html)

## What Dfetch Does

* Vendor source-only dependencies — fully self-contained, no external links at build time
* VCS-agnostic: mix Git, SVN, and plain archive URLs freely in one manifest
* Fetch and verify archives with cryptographic integrity checks
* Apply local patches while keeping upstream syncable (`dfetch diff` / `dfetch format-patch`)
* Supply-chain ready: SBOM generation, license detection, multi-format CI reports
* Migrate from Git submodules or SVN externals in seconds (`dfetch import`)
* Declarative code reuse across projects ([inner sourcing](https://about.gitlab.com/topics/version-control/what-is-innersource/))

## Install

### Stable

```bash
pip install dfetch
```

### latest version

```bash
pip install git+https://github.com/dfetch-org/dfetch.git#egg=dfetch
```

### Binary distributions

Each release on the [releases page](https://github.com/dfetch-org/dfetch/releases) provides installers for all major platforms.

- Linux `.deb` & `.rpm`
- macOS `.pkg`
- Windows `.msi`

## Example manifest

```yaml
manifest:
  version: 0.0

  remotes:                                                        # declare common sources in one place
  - name: github
    url-base: https://github.com/                                 # Allow git modules
    default: true                                                 # Set it as default

  - name: sourceforge
    url-base: svn://svn.code.sf.net/p/

  projects:

  - name: cpputest-git-tag
    dst: Tests/cpputest-git-tag
    url: https://github.com/cpputest/cpputest.git                 # Use external git directly
    tag: v3.4                                                     # revision can also be a tag

  - name: tortoise-svn-branch-rev
    dst: Tests/tortoise-svn-branch-rev/
    remote: sourceforge
    branch: 1.10.x
    revision: '28553'
    src: src/*
    vcs: svn
    repo-path: tortoisesvn/code

  - name: tortoise-svn-tag
    dst: Tests/tortoise-svn-tag/
    remote: sourceforge
    tag: version-1.13.1
    src: src/*.txt
    vcs: svn
    repo-path: tortoisesvn/code

  - name: cpputest-git-src
    dst: Tests/cpputest-git-src
    repo-path: cpputest/cpputest.git
    src: src

  - name: my-library
    dst: ext/my-library
    url: https://example.com/releases/my-library-1.0.tar.gz
    vcs: archive
    integrity:
      hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

## GitHub Action

You can use Dfetch in your GitHub Actions workflow to check your dependencies.
The results will be uploaded to GitHub. Add the following to your workflow file:

```yaml
jobs:
  dfetch-check:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - name: Run Dfetch Check
        uses: dfetch-org/dfetch@main
        with:
          working-directory: '.' # optional, defaults to project root
```
