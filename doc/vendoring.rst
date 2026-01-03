

Vendoring
=========

Vendoring is the practice of copying the source code of another project directly
into your own project's repository. Instead of relying on a package manager to
fetch dependencies at build or install time, the dependency code is stored
alongside the project itself and treated as part of the source tree.

Although the definition is simple, vendoring has long been controversial. Some
engineers see it as a practical way to gain control and reliability, while others
have historically described it as an anti-pattern. Both views exist for good
reasons, and understanding the trade-offs matters more than choosing a side.

What People Mean by Vendoring
-----------------------------

At a basic level, vendoring means that a project can be built using only what is
present in its repository. No network access is required, no external registries
need to be available, and no global package cache is assumed. Checking out a
specific revision of the repository is sufficient to reproduce a build from that
point in time.

The term originally became common in communities that explicitly placed third-
party code into directories named `vendor`. Over time, the word broadened to
describe any approach where dependency source code is copied into the project,
regardless of directory layout or tooling.

Vendoring does not necessarily imply permanent forks or heavy modification of
third-party code. In many cases, vendored dependencies are kept pristine and
updated mechanically from upstream sources.

Why Vendoring Can Be Helpful
----------------------------

The strongest argument for vendoring is reproducibility.

When dependencies are fetched dynamically, builds implicitly depend on the
continued availability and behavior of external services. Registries can go
offline, packages can be removed or yanked, and transitive dependencies can change
in ways that are difficult to predict. Vendoring removes these uncertainties by
making the build inputs explicit and local.

Vendoring also improves visibility. When dependency code lives in the same source
tree, it is easier to inspect, debug, and understand. Developers can step into
library code without context switching or relying on tooling to fetch sources on
demand. This visibility can reveal how much code a project is actually relying on,
especially when compared to the apparent simplicity of a short dependency list in
a configuration file.

Another benefit is reduced exposure to supply chain risk. Vendoring does not make
third-party code safe, but it shifts trust from live infrastructure to explicit
review. The project decides when dependencies are updated and exactly what code is
being included.

Some proponents also argue that vendoring creates a healthy friction around
dependencies. When adding a dependency requires consciously pulling in its source
code, teams may be more selective and more aware of the long-term cost of that
decision.

The Costs and Risks of Vendoring
--------------------------------

Vendoring introduces real downsides.

One common criticism is that vendoring discards upstream version control history.
When code is copied into another repository, its original commit history, tags,
and branches are no longer directly visible. This can make updates harder,
especially if vendored code has been locally modified.

Vendoring can also encourage divergence. When dependency code is nearby and easy
to change, there is a temptation to patch it locally rather than contribute fixes
upstream. Over time, this can result in silent forks that are difficult to
maintain or reconcile with new releases.

Repository size and noise are practical concerns as well. Vendored dependencies
increase clone size and can dominate diffs during updates. Large dependency
refreshes can obscure meaningful changes to the project's own code, making review
and merging more difficult.

Maintenance responsibility is another cost. Vendored dependencies do not update
themselves. Security fixes, bug fixes, and compatibility updates must be pulled in
manually. Without a clear policy and tooling support, vendored code can easily
become outdated.

Transitive Dependencies
-----------------------

Vendoring becomes significantly more complex once transitive dependencies are
considered.

Vendoring a single library often requires vendoring everything that library
depends on, and everything those dependencies rely on in turn. For ecosystems
with deep or fast-moving dependency graphs, this can quickly become a substantial
burden.

Package managers largely exist to manage this complexity by resolving dependency
graphs, handling version conflicts, and sharing common dependencies across
projects. Vendoring replaces that automation with explicit ownership, which is
sometimes desirable and sometimes overwhelming.

A Brief History
---------------

Vendoring predates modern package managers.

Early C and C++ projects routinely shipped third-party libraries inline because
there was no reliable way to depend on system-installed packages. Many Unix
programs were distributed as self-contained source releases that included all
required code.

As centralized package registries and dependency managers matured, vendoring
became less common and was sometimes criticized as outdated or unprofessional.
Automated updates, shared caches, and smaller repositories were seen as clear
wins.

Interest in vendoring returned as software supply chain risks became more visible.
Registry outages, dependency hijacks, and ecosystem fragility highlighted the
costs of relying entirely on external infrastructure.

Today, vendoring is best understood as a trade-off rather than a relic.

Vendoring Across Languages
--------------------------

Different language ecosystems have adopted vendoring to very different degrees.

Go is strongly associated with vendoring. Early versions of Go lacked a central
dependency manager, which made vendoring a practical solution. Even after the
introduction of module support, vendoring remains a first-class workflow, with
tooling that understands and prioritizes vendored dependencies. One of Go's proverbs
is "A little copying is better than a little dependency."

Rust supports vendoring but does not encourage it by default. The Rust ecosystem
places a strong emphasis on reproducibility through its package registry and lock
files, reducing the need for vendoring in everyday development. Vendoring is still
common in embedded systems, regulated environments, and long-term-support
projects.

JavaScript occupies an unusual position. Dependency source code is typically
present locally in directories such as `node_modules`, but it is rarely checked
into version control due to size and churn. Fully vendoring dependencies is
possible but uncommon.

Python has a mixed history. Vendoring was common in earlier projects and remains
common in small tools, embedded Python environments, and source-distributed
applications. Modern Python development more often relies on virtual environments
and lock files, but vendoring has never disappeared entirely.

C and C++ continue to vendor dependencies frequently. The lack of a universal
package manager, combined with ABI compatibility concerns and platform
differences, makes vendoring a practical and sometimes unavoidable choice.

Conclusion
----------

Vendoring is neither a best practice nor an anti-pattern.

It is a deliberate trade-off that exchanges convenience and automatic updates for
control, predictability, and independence from external systems. In some contexts,
that trade is clearly worthwhile. In others, it introduces more cost than benefit.

Used intentionally and with an understanding of its limitations, vendoring is
simply one tool among many for managing dependencies.

Best Practices
--------------

The following practices are drawn from our own usage of *Dfetch* and real-world policies and respected guidelines.
They *mitigate* vendoring risks; they do not eliminate them.

.. admonition :: Explicit Version Pinning and Provenance

    Every vendored dependency must be pinned to an explicit version, tag, or commit, and its source must be documented.

    **Rationale** Vendored code is often added once and then forgotten. Without automation, vulnerabilities, license issues,
    and inconsistencies can persist unnoticed long after initial inclusion.

    * pip: `vendor.txt` tracks versions and sources
    * Go/Kubernetes: `go.mod`, `go.sum`, `vendor/modules.txt`
    * Cargo: `Cargo.lock` + vendored sources
    * Guidelines: `OWASP SCVS <https://scvs.owasp.org/scvs/v1-inventory/>`_, OpenSSF, NIST SP 800-161, SLSA

    *Dfetch* addresses this by having a declarative :ref:`manifest` and the option to :ref:`freeze` dependences to make each
    revision explicit.

.. admonition :: Reproducible and Offline Builds

    Vendoring must enable fully reproducible and offline builds.

    **Rationale** The point of vendoring code is to remove external dependencies, by making sure an offline build succeeds it is
    proven that builds are not dependent on external sources.

    * Go: committed `vendor/`
    * Cargo: `.cargo/config.toml` + `cargo vendor`
    * pip: vendored wheels and pure-Python dependencies
    * Guidelines: SLSA, OpenSSF

    *Dfetch* doesn't directly address this, this is a policy to follow.

.. admonition :: Trust Upstream After Due Diligence

    Vendored dependencies are not reviewed line-by-line, upstream (unit) tests are not run.
    Do not auto-format vendored code.

    **Rationale** Reviewing every line of external code is costly and rarely effective. By performing due diligence
    on upstream sources, you can trust their correctness and security while minimizing maintenance burden.

    Reviewers should verify:

    * Version changes and pinning
    * Changelogs and release notes for regressions or security issues
    * License compatibility
    * CI status and test results of the upstream project
    * Evidence of active maintenance and community support

    Do not run upstream unit tests locally, apply formatting or style changes, or make cosmetic changes to vendored code.

    This principle is aligned with:

    * OWASP Software Component Verification Standard
    * Google Open Source Security Guidelines
    * OpenSSF Best Practices

    *Dfetch* supports this approach via its manifest and metadata file (``.dfetch_data.yaml``), which can be reviewed independently
    of the vendored code itself.


.. admonition :: Separation of Vendor Updates from Product Changes

    Vendored dependency updates must be isolated from functional code changes.

    * Separate PRs or commits
    * Clear commit messages documenting versions and rationale

    **Rationale** By separation the review noise will be reduced, letting maintainers focus on important changes.

    *Dfetch* doesn't address this directly.

.. admonition :: Minimize Local Modifications

    Vendored code must not be modified directly unless unavoidable.

    If modifications are required:

    * Document patches explicitly
    * Prefer patch/overlay mechanisms
    * Upstream changes whenever possible
    * pip: documented adaptations
    * Cargo: `[patch]` mechanism
    * Guidelines: Google OSS, OWASP, OpenSSF

    **Rationale** The vendored dependency may diverge, keeping it the same as upstream makes it easy to keep following
    upstream updates. Also by upstreaming any changes, more people outside the project can profit from any fixes.

    *Dfetch* addresses this by providing a ``dfetch diff`` (:ref:`Diff`) command and a ``patch`` :ref:`Patch` attribute in the manifest.
    Next to this there is a CI system to detect local changes using :ref:`Check`.

.. admonition :: Continuous Automation and Security Scanning

    Vendored dependencies must be continuously verified through automation.

    * CI verifies vendor consistency
    * Dependency and CVE scanning
    * SBOM generation

    **Rationale** By copy-pasting a dependency, there maybe silent security degradation since there is no automatic updates.

    *Dfetch* addresses this by providing a ``dfetch check`` (:ref:`Check`) command to see if vendored dependencies are out-of-date and
    various report formats (including SBoM) to check vulnerabilities.

.. admonition :: Track License and Legal Information

    All vendored dependencies must have their license and legal information explicitly recorded.

    **Rationale** Ensuring license compliance prevents legal issues and maintains compatibility with your project's license.

    * Track license type for each vendored dependency.
    * Use machine-readable formats where possible (e.g., SPDX identifiers).
    * Include license documentation alongside vendored code.
    * Guidelines: OWASP, OpenSSF, Google OSS best practices.

    *Dfetch* addresses this by even when only a subfolder is fetched, retaining the license file.

.. admonition :: Vendor Only What You Need

    Minimize vendored code to what is strictly necessary for your project.

    **Rationale** Vendoring unnecessary code increases maintenance burden, security risk, and potential for patch rot.
    Include only the specific modules, packages, subfolder or components your project depends on.

    *Dfetch* enables this by allowing to fetch only a subfolder using the ``src:`` attribute.

.. admonition :: Isolate Vendored Dependencies

    Vendored dependencies must be clearly isolated from first-party code.

    **Rationale** Isolation prevents accidental coupling, avoids namespace conflicts, and makes audits, updates, and
    removals easier. Vendored code should be unmistakably identifiable as third-party code.

    * Place vendored dependencies in a clearly named and well-known directory (e.g. ``vendor/``, ``_vendor/``).
    * Avoid mixing vendored code with product or library sources.
    * Use language-supported namespace or module isolation where available.
    * Prevent accidental imports of vendored internals by first-party code.
    * Keep vendored code mechanically separable to enable future un-vendoring.

    This principle follows established practices in:

    * Go (``vendor/`` directory)
    * pip (``pip/_vendor``)
    * Cargo (``vendor/`` layout)
    * Google OSS and OpenSSF guidelines

    *Dfetch* enables this by allowing to store the vendored dependency in a folder using the ``dst:`` attribute.

Real-world projects using vendoring
-----------------------------------

- `Dynaconf - (Python) <https://github.com/dynaconf/dynaconf/tree/master/dynaconf/vendor>`_
- `PIP - (Python) <https://github.com/pypa/pip/tree/main/src/pip/_vendor>`_
- `Kubernetes - (Go) <https://github.com/kubernetes/kubernetes/tree/master/vendor>`_
- `Cargo - (Rust) <https://doc.rust-lang.org/cargo/commands/cargo-vendor.html>`_

Real world projects using Dfetch
--------------------------------

Here are some links to example projects using *Dfetch*.

- `Dfetch`: https://github.com/dfetch-org/dfetch
- `ModbusScope`: https://github.com/ModbusScope/ModbusScope

Internally we use *Dfetch* for various projects and uses.


Further Reading
---------------

- `Vendoring is a vile anti pattern - Michael F. Lamb <https://gist.github.com/datagrok/8577287>`_
- `SO: What is "vendoring"? - Niels Bom <https://stackoverflow.com/questions/26217488/what-is-vendoring>`_
- `Why we stopped vendoring our dependencies - Carlos Perez <https://web.archive.org/web/20180216205752/http://blog.bithound.io/why-we-stopped-vendoring-our-npm-dependencies/>`_
- `Vendoring - Carson Gross <https://htmx.org/essays/vendoring/>`_
- `Our Software Dependency Problem - Russ Cox <https://research.swtch.com/deps>`_
- `On Managing External Dependencies - Phillip Johnston <https://embeddedartistry.com/blog/2020/06/22/qa-on-managing-external-dependencies/>`_
- `PIP's vendoring policy <https://github.com/pypa/pip/blob/main/src/pip/_vendor/README.rst>`_
- `SubPatch benefits <https://subpatch.net/exp/benefits/>`_
