

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
------------------------------

At a basic level, vendoring means that a project can be built using only what is
present in its repository. No network access is required, no external registries
need to be available, and no global package cache is assumed. Checking out a
specific revision of the repository is sufficient to reproduce a build from that
point in time.

The term originally became common in communities that explicitly placed third-
party code into directories named ``vendor``. Over time, the word broadened to
describe any approach where dependency source code is copied into the project,
regardless of directory layout or tooling.

Vendoring does not necessarily imply permanent forks or heavy modification of
third-party code. In many cases, vendored dependencies are kept pristine and
updated mechanically from upstream sources.

----

.. div:: band-tint

   :material-regular:`thumb_up;2em;sd-text-primary` **Why vendoring can be helpful**

   .. grid:: 1 1 2 2
      :gutter: 3

      .. grid-item-card:: :material-regular:`replay;2em` Reproducibility
         :text-align: center
         :class-card: stat-card

         When dependencies are fetched dynamically, builds implicitly depend on the
         availability of external services. Vendoring makes build inputs **explicit and
         local** — no registry, no CDN, no network required.

      .. grid-item-card:: :material-regular:`visibility;2em` Visibility
         :text-align: center
         :class-card: stat-card

         Dependency code lives in the same source tree.
         Easier to **inspect, debug, and understand** — no context switching,
         no tooling required to fetch sources on demand.

      .. grid-item-card:: :material-regular:`security;2em` Supply-chain trust
         :text-align: center
         :class-card: stat-card

         Vendoring shifts trust from live infrastructure to explicit review.
         The project decides **when** dependencies are updated and **exactly what
         code** is being included.

      .. grid-item-card:: :material-regular:`tune;2em` Healthy friction
         :text-align: center
         :class-card: stat-card

         When adding a dependency requires consciously pulling in its source code,
         teams become **more selective** and more aware of the long-term cost of
         that decision.

----

.. div:: band-mint

   :material-regular:`warning;2em;sd-text-primary` **The costs and risks of vendoring**

   .. grid:: 1 1 2 2
      :gutter: 3

      .. grid-item-card:: :material-regular:`history_toggle_off;2em` History loss
         :text-align: center
         :class-card: stat-card

         When code is copied into another repository, its original commit history,
         tags, and branches are no longer directly visible. This can make updates
         **harder**, especially if vendored code has been locally modified.

      .. grid-item-card:: :material-regular:`call_split;2em` Divergence risk
         :text-align: center
         :class-card: stat-card

         When dependency code is nearby and easy to change, there is a temptation
         to patch it locally rather than contribute fixes upstream. Over time this
         can create **silent forks** that are difficult to reconcile.

      .. grid-item-card:: :material-regular:`storage;2em` Repository size
         :text-align: center
         :class-card: stat-card

         Vendored dependencies increase clone size and can **dominate diffs**
         during updates. Large dependency refreshes can obscure meaningful changes
         to the project's own code, making review and merging harder.

      .. grid-item-card:: :material-regular:`build;2em` Maintenance burden
         :text-align: center
         :class-card: stat-card

         Vendored dependencies do not update themselves. Security fixes, bug fixes,
         and compatibility updates must be **pulled in manually**. Without a clear
         policy and tooling support, vendored code can easily become outdated.


Transitive Dependencies
-----------------------

:material-regular:`account_tree;1.2em;sd-text-primary` Vendoring becomes significantly more complex once transitive dependencies are
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

:material-regular:`history;1.2em;sd-text-primary` Vendoring predates modern package managers.

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

:material-regular:`code;1.2em;sd-text-primary` Different language ecosystems have adopted vendoring to very different degrees.

.. grid:: 1 1 3 3
   :gutter: 2

   .. grid-item-card:: Go
      :text-align: center
      :class-card: stat-card

      :material-regular:`check_circle;1.5em;sd-text-primary`

      Strongly associated with vendoring.
      First-class workflow via ``go mod vendor``.
      *"A little copying is better than a little dependency."*

   .. grid-item-card:: Rust
      :text-align: center
      :class-card: stat-card

      :material-regular:`check_circle;1.5em;sd-text-primary`

      Supported but not the default. Common in **embedded, regulated, and
      long-term-support** projects where reproducibility is paramount.

   .. grid-item-card:: C / C++
      :text-align: center
      :class-card: stat-card

      :material-regular:`check_circle;1.5em;sd-text-primary`

      **Frequent** vendoring due to the lack of a universal package manager,
      ABI compatibility concerns, and platform differences.

   .. grid-item-card:: JavaScript
      :text-align: center
      :class-card: stat-card

      :material-regular:`warning;1.5em`

      ``node_modules`` is local, but **rarely committed** due to size and churn.
      Fully vendoring is possible but uncommon.

   .. grid-item-card:: Python
      :text-align: center
      :class-card: stat-card

      :material-regular:`warning;1.5em`

      Mixed history. Common in **small tools and embedded environments**.
      Modern development more often relies on virtual environments and lock files.

   .. grid-item-card:: Java / JVM
      :text-align: center
      :class-card: stat-card

      :material-regular:`remove_circle;1.5em`

      Rarely vendored. Maven and Gradle ecosystems rely heavily on remote
      repositories and dependency resolution.


Conclusion
----------

.. card::
   :class-card: card-tinted

   :material-regular:`balance;2em;sd-text-primary` **Vendoring is neither a best practice nor an anti-pattern.**

   It is a deliberate trade-off that exchanges convenience and automatic updates for
   control, predictability, and independence from external systems. In some contexts,
   that trade is clearly worthwhile. In others, it introduces more cost than benefit.

   Used intentionally and with an understanding of its limitations, vendoring is
   simply one tool among many for managing dependencies.

----

Best Practices
--------------

The following practices are drawn from our own usage of *Dfetch* and real-world
policies and respected guidelines. They *mitigate* vendoring risks; they do not
eliminate them.

.. card:: :material-regular:`push_pin;1.5em;sd-text-primary` Explicit Version Pinning and Provenance

   Every vendored dependency must be pinned to an explicit version, tag, or commit,
   and its source must be documented.

   **Rationale** Vendored code is often added once and then forgotten. Without
   automation, vulnerabilities, license issues, and inconsistencies can persist
   unnoticed long after initial inclusion.

   * pip: ``vendor.txt`` tracks versions and sources
   * Go/Kubernetes: ``go.mod``, ``go.sum``, ``vendor/modules.txt``
   * Cargo: ``Cargo.lock`` + vendored sources
   * Guidelines: `OWASP SCVS <https://scvs.owasp.org/scvs/v1-inventory/>`_, OpenSSF, NIST SP 800-161, SLSA

   *Dfetch* addresses this by having a declarative :ref:`manifest` and the option to :ref:`freeze`
   dependencies to make each revision explicit.

.. card:: :material-regular:`offline_bolt;1.5em;sd-text-primary` Reproducible and Offline Builds

   Vendoring must enable fully reproducible and offline builds.

   **Rationale** The point of vendoring code is to remove external dependencies.
   By making sure an offline build succeeds, it is proven that builds are not
   dependent on external sources.

   * Go: committed ``vendor/``
   * Cargo: ``.cargo/config.toml`` + ``cargo vendor``
   * pip: vendored wheels and pure-Python dependencies
   * Guidelines: SLSA, OpenSSF

   *Dfetch* doesn't directly address this — this is a policy to follow.

.. card:: :material-regular:`verified;1.5em;sd-text-primary` Trust Upstream After Due Diligence

   Vendored dependencies are not reviewed line-by-line; upstream unit tests are not
   run. Do not auto-format vendored code.

   **Rationale** Reviewing every line of external code is costly and rarely effective.
   By performing due diligence on upstream sources, you can trust their correctness
   and security while minimising maintenance burden.

   Reviewers should verify:

   * Version changes and pinning
   * Changelogs and release notes for regressions or security issues
   * License compatibility
   * CI status and test results of the upstream project
   * Evidence of active maintenance and community support

   Do not run upstream unit tests locally, apply formatting or style changes, or
   make cosmetic changes to vendored code.

   Aligned with: OWASP SCVS · Google Open Source Security Guidelines · OpenSSF Best Practices.

   *Dfetch* supports this approach via its manifest and metadata file
   (``.dfetch_data.yaml``), which can be reviewed independently of the vendored code itself.

.. card:: :material-regular:`compare_arrows;1.5em;sd-text-primary` Separation of Vendor Updates from Product Changes

   Vendored dependency updates must be isolated from functional code changes.

   * Separate PRs or commits
   * Clear commit messages documenting versions and rationale

   **Rationale** Separation reduces review noise, letting maintainers focus on
   meaningful changes.

   *Dfetch* doesn't address this directly.

.. card:: :material-regular:`edit_off;1.5em;sd-text-primary` Minimize Local Modifications

   Vendored code must not be modified directly unless unavoidable.

   If modifications are required:

   * Document patches explicitly
   * Prefer patch/overlay mechanisms
   * Upstream changes whenever possible
   * Cargo: ``[patch]`` mechanism
   * Guidelines: Google OSS, OWASP, OpenSSF

   **Rationale** Keeping the vendored dependency identical to upstream makes it easy
   to follow upstream updates. Upstreaming any changes lets others in the wider
   community benefit from your fixes.

   *Dfetch* addresses this by providing a ``dfetch diff`` (:ref:`Diff`) command and a
   ``patch`` (:ref:`Patch`) attribute in the manifest. It also has a CI check to detect
   local changes using :ref:`Check`.

.. card:: :material-regular:`verified_user;1.5em;sd-text-primary` Continuous Automation and Security Scanning

   Vendored dependencies must be continuously verified through automation.

   * CI verifies vendor consistency
   * Dependency and CVE scanning
   * SBOM generation

   **Rationale** By copy-pasting a dependency, there may be silent security
   degradation since there are no automatic updates.

   *Dfetch* addresses this by providing a ``dfetch check`` (:ref:`Check`) command to
   see if vendored dependencies are out-of-date and various report formats (including
   SBoM) to check vulnerabilities.

.. card:: :material-regular:`gavel;1.5em;sd-text-primary` Track License and Legal Information

   All vendored dependencies must have their license and legal information explicitly
   recorded.

   **Rationale** Ensuring license compliance prevents legal issues and maintains
   compatibility with your project's license.

   * Track license type for each vendored dependency
   * Use machine-readable formats where possible (e.g. SPDX identifiers)
   * Include license documentation alongside vendored code
   * Guidelines: OWASP, OpenSSF, Google OSS best practices

   *Dfetch* addresses this by retaining the license file even when only a subfolder
   is fetched.

.. card:: :material-regular:`filter_alt;1.5em;sd-text-primary` Vendor Only What You Need

   Minimise vendored code to what is strictly necessary for your project.

   **Rationale** Vendoring unnecessary code increases maintenance burden, security
   risk, and potential for patch rot. Include only the specific modules, packages,
   subfolder, or components your project depends on.

   *Dfetch* enables this by allowing you to fetch only a subfolder using the ``src:``
   attribute.

.. card:: :material-regular:`workspaces;1.5em;sd-text-primary` Isolate Vendored Dependencies

   Vendored dependencies must be clearly isolated from first-party code.

   **Rationale** Isolation prevents accidental coupling, avoids namespace conflicts,
   and makes audits, updates, and removals easier. Vendored code should be
   unmistakably identifiable as third-party code.

   * Place vendored dependencies in a clearly named directory (e.g. ``vendor/``, ``_vendor/``)
   * Avoid mixing vendored code with product or library sources
   * Use language-supported namespace or module isolation where available
   * Keep vendored code mechanically separable to enable future un-vendoring

   Follows established practices in: Go (``vendor/``) · pip (``pip/_vendor``) · Cargo (``vendor/``) · Google OSS / OpenSSF.

   *Dfetch* enables this by allowing you to store the vendored dependency in a folder
   using the ``dst:`` attribute.

----

.. div:: band-tint

   :material-regular:`public;2em;sd-text-primary` **Real-world projects using vendoring**

   .. grid:: 1 1 2 2
      :gutter: 2

      .. grid-item-card:: Dynaconf (Python)
         :link: https://github.com/dynaconf/dynaconf/tree/master/dynaconf/vendor
         :link-type: url

         :material-regular:`code;1.2em` Python configuration management library.

      .. grid-item-card:: pip (Python)
         :link: https://github.com/pypa/pip/tree/main/src/pip/_vendor
         :link-type: url

         :material-regular:`code;1.2em` Python's own package installer vendors its dependencies.

      .. grid-item-card:: Kubernetes (Go)
         :link: https://github.com/kubernetes/kubernetes/tree/master/vendor
         :link-type: url

         :material-regular:`code;1.2em` The industry-standard container orchestrator.

      .. grid-item-card:: Cargo (Rust)
         :link: https://doc.rust-lang.org/cargo/commands/cargo-vendor.html
         :link-type: url

         :material-regular:`code;1.2em` Rust's package manager supports vendoring natively.


.. div:: band-mint

   :material-regular:`bolt;2em;sd-text-primary` **Real-world projects using Dfetch**

   .. grid:: 1 1 2 2
      :gutter: 2

      .. grid-item-card:: Dfetch
         :link: https://github.com/dfetch-org/dfetch
         :link-type: url

         :material-regular:`hub;1.2em` Dfetch uses itself to vendor its own test fixtures.

      .. grid-item-card:: ModbusScope
         :link: https://github.com/ModbusScope/ModbusScope
         :link-type: url

         :material-regular:`hub;1.2em` Industrial Modbus visualisation tool.

      .. grid-item-card:: Example Yocto
         :link: https://github.com/dfetch-org/example-yocto
         :link-type: url

         :material-regular:`hub;1.2em` Dfetch in a Yocto/embedded Linux build.

      .. grid-item-card:: Example Zephyr
         :link: https://github.com/dfetch-org/example-zephyr
         :link-type: url

         :material-regular:`hub;1.2em` Dfetch in a Zephyr RTOS project.

   Internally we use *Dfetch* for various projects and uses.


Further Reading
---------------

:material-regular:`menu_book;1.2em;sd-text-primary`

* `Vendoring is a vile anti pattern — Michael F. Lamb <https://gist.github.com/datagrok/8577287>`_
* `SO: What is "vendoring"? — Niels Bom <https://stackoverflow.com/questions/26217488/what-is-vendoring>`_
* `Why we stopped vendoring our dependencies — Carlos Perez <https://web.archive.org/web/20180216205752/http://blog.bithound.io/why-we-stopped-vendoring-our-npm-dependencies/>`_
* `Vendoring — Carson Gross <https://htmx.org/essays/vendoring/>`_
* `Our Software Dependency Problem — Russ Cox <https://research.swtch.com/deps>`_
* `On Managing External Dependencies — Phillip Johnston <https://embeddedartistry.com/blog/2020/06/22/qa-on-managing-external-dependencies/>`_
* `PIP's vendoring policy <https://github.com/pypa/pip/blob/main/src/pip/_vendor/README.rst>`_
* `SubPatch benefits <https://subpatch.net/exp/benefits/>`_
