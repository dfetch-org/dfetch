.. Dfetch documentation master file

Vendoring Dependencies
======================

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

Real-world projects using vendoring
-----------------------------------

- `Dynaconf - (Python) <https://github.com/dynaconf/dynaconf/tree/master/dynaconf/vendor>`_
- `PIP - (Python) <https://github.com/pypa/pip/tree/main/src/pip/_vendor>`_
- `Kubernetes - (Go) <https://github.com/kubernetes/kubernetes/tree/master/vendor>`_
- `Cargo - (Rust) <https://doc.rust-lang.org/cargo/commands/cargo-vendor.html>`_


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
