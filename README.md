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


**DFetch can manage dependencies**

We make products that can last 15+ years; because of this we want to be able to have all sources available
to build the entire project from source without depending on external resources.
For this, we needed a dependency manager that was flexible enough to retrieve dependencies as plain text
from various sources. `svn externals`, `git submodules` and `git subtrees` solve a similar
problem, but not in a VCS-agnostic way or completely user-friendly way.
We want self-contained code repositories without any hassle for end-users.
Dfetch must promote upstreaming changes, but allow for local customizations.
The problem is described thoroughly in [managing external dependencies](https://embeddedartistry.com/blog/2020/06/22/qa-on-managing-external-dependencies/) and sometimes
is also known as [*vendoring*](https://dfetch.readthedocs.io/en/latest/vendoring.html).

Other tools that do similar things are ``Zephyr's West``, ``CMake ExternalProject`` and other meta tools.
See [alternatives](https://dfetch.readthedocs.io/en/latest/alternatives.html) for a complete list.

[**Getting started**](https://dfetch.readthedocs.io/en/latest/getting_started.html) |
[**Manual**](https://dfetch.readthedocs.io/en/latest/manual.html) |
[**Troubleshooting**](https://dfetch.readthedocs.io/en/latest/troubleshooting.html)  |
[**Contributing**](https://dfetch.readthedocs.io/en/latest/contributing.html)

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

## Github Action

You can use DFetch in your Github Actions workflow to check your dependencies.
The results will be uploaded to Github. Add the following to your workflow file:

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
