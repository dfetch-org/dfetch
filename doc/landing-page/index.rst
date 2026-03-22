.. Dfetch documentation master file

:sd_hide_title:

.. meta::
   :description: Dfetch vendors source code from Git and SVN repositories directly into your project. No submodules, no lock-in, fully self-contained.
   :keywords: dfetch, dependency management, vendoring, git, svn, embedded development, source-only dependencies, multi-repo, supply chain, sbom, license compliance
   :author: Dfetch Contributors
   :google-site-verification: rXUIdonVCg6XtZUDdOd7fJdSNj3bOoJJRqCFn3OVb04

.. raw:: html

   <meta property="og:title" content="Dfetch — Vendor dependencies without the pain">
   <meta property="og:description" content="VCS-agnostic source-only dependency management. Works with Git and SVN. No submodules, no lock-in, supply-chain ready.">
   <meta property="og:image" content="https://dfetch.rtfd.io/static/dfetch-logo.png">
   <meta property="og:url" content="https://dfetch-org.github.io">

   <meta name="twitter:card" content="summary_large_image">
   <meta name="twitter:title" content="Dfetch — Vendor dependencies without the pain">
   <meta name="twitter:description" content="VCS-agnostic source-only dependency management. Works with Git and SVN. No submodules, no lock-in, supply-chain ready.">
   <meta name="twitter:image" content="https://dfetch.rtfd.io/static/dfetch-logo.png">

.. image:: ../images/dfetch_header.png
   :width: 100%
   :align: center


Dfetch
######

**Vendor dependencies without the pain.**

**Dfetch** copies source code directly into your project — no Git submodules, no SVN externals,
no hidden external links. Dependencies live as plain, readable files inside your own repository.
You stay in full control of every line.

.. grid:: 3

    .. grid-item::

      .. button-link:: https://github.com/dfetch-org/dfetch/releases/latest
         :color: primary
         :shadow:
         :expand:

         :material-regular:`download;2em` Download

    .. grid-item::

      .. button-link:: https://dfetch.rtfd.io/
         :color: secondary
         :shadow:
         :expand:

         :material-regular:`description;2em` Docs

    .. grid-item::

      .. button-link:: https://github.com/dfetch-org/dfetch/
         :color: secondary
         :shadow:
         :expand:

         :material-regular:`article;2em` Source


.. div:: how-it-works

   **How it works**

   .. grid:: 1 1 3 3
      :gutter: 0

      .. grid-item::
         :class: how-step

         .. div:: step-num

            1

         **Install**

         Download or ``pip install dfetch``

      .. grid-item::
         :class: how-step

         .. div:: step-num

            2

         **Configure**

         Add projects to ``dfetch.yaml``

      .. grid-item::
         :class: how-step

         .. div:: step-num

            3

         **Fetch**

         ``dfetch update``


.. div:: install-options

   :material-regular:`devices;1.5em;sd-text-primary` **Available on every platform**

   .. grid:: 2 2 4 4
      :gutter: 2

      .. grid-item-card:: :material-regular:`terminal;1.75em` Linux
         :text-align: center
         :class-card: install-card
         :link: https://github.com/dfetch-org/dfetch/releases/latest
         :link-type: url

         ``.deb``  ·  ``.rpm``

      .. grid-item-card:: :material-regular:`laptop_mac;1.75em` macOS
         :text-align: center
         :class-card: install-card
         :link: https://github.com/dfetch-org/dfetch/releases/latest
         :link-type: url

         ``.pkg``

      .. grid-item-card:: :material-regular:`desktop_windows;1.75em` Windows
         :text-align: center
         :class-card: install-card
         :link: https://github.com/dfetch-org/dfetch/releases/latest
         :link-type: url

         ``.msi``

      .. grid-item-card:: :material-regular:`code;1.75em` Python / pip
         :text-align: center
         :class-card: install-card
         :link: https://pypi.org/project/dfetch/
         :link-type: url

         ``pip install dfetch``


.. div:: band-tint

   :material-regular:`play_circle;2em;sd-text-primary` **See it in action**

   .. asciinema:: ../asciicasts/basic.cast


.. div:: band-mint

   :material-regular:`stars;2em;sd-text-primary` **What makes Dfetch different**

   .. grid:: 1 1 3 3
      :gutter: 3

      .. grid-item-card:: :material-regular:`shuffle;2em` Any VCS, mixed freely
         :text-align: center
         :class-card: stat-card

         Works with **Git and SVN** — even mixed in the same project.
         The only dependency manager that bridges both without compromise.

      .. grid-item-card:: :material-regular:`code;2em` Any language, any build system
         :text-align: center
         :class-card: stat-card

         C, C++, Python, Go, Rust, Java — dfetch doesn't care.
         No build-system assumptions. Bring your own toolchain.

      .. grid-item-card:: :material-regular:`history;2em` Built for long lifecycles
         :text-align: center
         :class-card: stat-card

         Designed for long-lived embedded and industrial products.
         Reproducible builds from source — **no registry, no CDN, no service required**.


.. card:: :material-regular:`account_tree;1.5em` How it works — from manifest to vendored folder

   One project entry in ``dfetch.yaml``. One command. Dfetch copies exactly what you
   specified, pins the version in ``.dfetch_data.yaml``, and keeps everything inside your repository.

   .. div:: infographic-wrapper

      .. grid:: 1 1 2 2
         :gutter: 4

         .. grid-item::
            :columns: 12 12 7 7

            .. code-block:: yaml
               :caption: dfetch.yaml

               manifest:
                 version: '0.0'

                 remotes:
                   - name: github
                     url-base: https://github.com/

                 projects:
                   - name: ext/cunit  # (1)
                     remote: github
                     repo-path: org/cunit
                     tag: v3.2.7      # (2)
                     src: src/        # (3)

         .. grid-item::
            :columns: 12 12 5 5

            .. code-block:: text
               :caption: After dfetch update

               your-project/
               ├─ dfetch.yaml
               └─ ext/
                  └─ cunit/           (a)
                     ├─ .dfetch_data.yaml
                     ├─ LICENSE       (b)
                     └─ CUnit.h       (c)

   .. div:: infographic-legend

      .. grid:: 1 1 3 3
         :gutter: 2

         .. grid-item::

            **(1)** ``name:`` — destination path in your repo

         .. grid-item::

            **(2)** ``tag:`` — exact version to fetch

         .. grid-item::

            **(3)** ``src:`` — subfolder to copy from upstream

      .. grid:: 1 1 3 3
         :gutter: 2

         .. grid-item::

            **(a)** folder created at the path given by ``name:``

         .. grid-item::

            **(b)** license always retained, even with ``src:``

         .. grid-item::

            **(c)** contents of ``src:`` placed directly here


.. div:: why-dfetch

   **Why teams choose Dfetch**

   .. grid:: 1
      :gutter: 0

      .. grid-item::

         :material-regular:`shuffle;1.5em;sd-text-primary` **VCS-agnostic**

         Works seamlessly with **Git and SVN** — even mixed within the same project.
         Pin by tag, branch, revision, or exact commit hash. Adapt to your team's workflow, not the other way around.

      .. grid-item::

         :material-regular:`archive;1.5em;sd-text-primary` **Fully self-contained**

         Every dependency is stored **inside your repository** as plain source code.
         No external links means simpler audits, offline builds, and hassle-free deployments that stay reproducible forever.

      .. grid-item::

         :material-regular:`inventory_2;1.5em;sd-text-primary` **Fetch only what you need**

         Point *Dfetch* at a single subfolder inside a larger repo using the ``src:`` attribute.
         Pull in just the files you need — **no bloat, no noise**, and license files are always retained.

      .. grid-item::

         :material-regular:`lock_open;1.5em;sd-text-primary` **Zero lock-in**

         Your vendored code stays as plain source files. Switch tools any time — **no proprietary formats, no migration work**.
         *Dfetch* respects that your source code belongs to you.


.. card::  :material-regular:`done_all;4em;sd-text-primary` **Stay up to date — effortlessly**
   :class-card: sd-bg-dark sd-text-light

   Check which dependencies have available updates and pull them in when you are ready.
   *Dfetch* puts you in control of every change — no surprise breakages, no forced upgrades.

   .. asciinema:: ../asciicasts/check.cast


.. div:: band-tint

   :material-regular:`security;2em;sd-text-primary` **Supply-chain ready out of the box**

   .. grid:: 1 1 3 3
      :gutter: 3

      .. grid-item-card:: :material-regular:`receipt_long;2em` SBOM generation
         :text-align: center
         :class-card: stat-card

         Generate a machine-readable **Software Bill of Materials** to track every vendored dependency —
         ready for audits, compliance checks, and vulnerability scans.

      .. grid-item-card:: :material-regular:`balance;2em` Automatic license detection
         :text-align: center
         :class-card: stat-card

         Infers and reports the license for every dependency automatically.
         Stay legally compliant — **even when fetching a single subfolder** from a larger repository.

      .. grid-item-card:: :material-regular:`analytics;2em` Multi-format reports
         :text-align: center
         :class-card: stat-card

         Export to **Jenkins JSON, SARIF, Code Climate, DependencyTrack** formats.
         Plug into your existing security toolchain with zero extra work.


.. card:: :material-regular:`difference;4em;sd-text-primary` **Customize without losing upstream**
   :class-card: card-tinted

   Vendor a dependency, tweak it locally, and still stay current with upstream — *Dfetch* makes this safe.

   ``dfetch diff`` generates clean patch files from your local modifications.
   On every subsequent update those patches are **re-applied automatically**, keeping your customizations alive
   without forking. When you're ready, upstream the fix properly and drop the patch.


.. card:: :material-regular:`smart_toy;4em;sd-text-primary` **Built for modern CI/CD**
   :class-card: sd-bg-dark sd-text-light

   *Dfetch* plugs right into your automation pipeline, pushing dependency status to your existing tools automatically.

   .. raw:: html

      <svg class="ci-diagram" viewBox="0 0 600 420" xmlns="http://www.w3.org/2000/svg"
           role="img" aria-label="dfetch check reports quality status to GitHub, GitLab, Jenkins and Code Climate; dfetch report generates CycloneDX SBOM for GitHub, GitLab and DependencyTrack">
        <defs>
          <clipPath id="ci-check-clip">
            <rect x="10" y="20" width="155" height="60" rx="8"/>
          </clipPath>
          <clipPath id="ci-report-clip">
            <rect x="10" y="255" width="155" height="60" rx="8"/>
          </clipPath>
        </defs>

        <!-- dfetch check command box -->
        <rect x="10" y="20" width="155" height="60" rx="8"
              fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.14)" stroke-width="1.5"/>
        <rect x="10" y="20" width="4" height="60" fill="#4e7fa0" clip-path="url(#ci-check-clip)"/>
        <text x="88" y="50" text-anchor="middle" dominant-baseline="middle"
              font-family="JetBrains Mono,monospace" font-size="12">
          <tspan fill="#6ab0d4">$ </tspan><tspan fill="rgba(255,255,255,0.95)">dfetch check</tspan>
        </text>
        <rect x="140" y="43" width="6" height="12" rx="1" fill="#6ab0d4" opacity="0.7">
          <animate attributeName="opacity" values="0.7;0;0.7" dur="1.1s" repeatCount="indefinite"/>
        </rect>

        <!-- dfetch report command box -->
        <rect x="10" y="255" width="155" height="60" rx="8"
              fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.14)" stroke-width="1.5"/>
        <rect x="10" y="255" width="4" height="60" fill="#2da88e" clip-path="url(#ci-report-clip)"/>
        <text x="88" y="277" text-anchor="middle" dominant-baseline="middle"
              font-family="JetBrains Mono,monospace" font-size="12">
          <tspan fill="#5ecfb8">$ </tspan><tspan fill="rgba(255,255,255,0.95)">dfetch report</tspan>
        </text>
        <text x="88" y="296" text-anchor="middle" dominant-baseline="middle"
              font-family="JetBrains Mono,monospace" font-size="11"
              fill="rgba(255,255,255,0.5)">-t sbom</text>
        <rect x="122" y="290" width="6" height="10" rx="1" fill="#5ecfb8" opacity="0.7">
          <animate attributeName="opacity" values="0.7;0;0.7" dur="1.3s" begin="-0.6s" repeatCount="indefinite"/>
        </rect>

        <!-- CHECK: track lines -->
        <path id="ck-p1" d="M 165,50 C 292,50 292,30  420,30"  class="ci-line"/>
        <path id="ck-p2" d="M 165,50 C 292,50 292,88  420,88"  class="ci-line"/>
        <path id="ck-p3" d="M 165,50 C 292,50 292,146 420,146" class="ci-line"/>
        <path id="ck-p4" d="M 165,50 C 292,50 292,204 420,204" class="ci-line"/>

        <!-- CHECK dots — amber -->
        <circle r="3.5" fill="#c2620a"><animateMotion dur="1.5s" begin="0s"      repeatCount="indefinite" calcMode="linear"><mpath href="#ck-p1"/></animateMotion></circle>
        <circle r="3.5" fill="#c2620a"><animateMotion dur="1.5s" begin="-0.375s" repeatCount="indefinite" calcMode="linear"><mpath href="#ck-p2"/></animateMotion></circle>
        <circle r="3.5" fill="#c2620a"><animateMotion dur="1.5s" begin="-0.75s"  repeatCount="indefinite" calcMode="linear"><mpath href="#ck-p3"/></animateMotion></circle>
        <circle r="3.5" fill="#c2620a"><animateMotion dur="1.5s" begin="-1.125s" repeatCount="indefinite" calcMode="linear"><mpath href="#ck-p4"/></animateMotion></circle>

        <!-- REPORT: track lines -->
        <path id="rp-p1" d="M 165,285 C 292,285 292,273 420,273" class="ci-line"/>
        <path id="rp-p2" d="M 165,285 C 292,285 292,331 420,331" class="ci-line"/>
        <path id="rp-p3" d="M 165,285 C 292,285 292,389 420,389" class="ci-line"/>

        <!-- REPORT dots — teal -->
        <circle r="3.5" fill="#2da88e"><animateMotion dur="1.5s" begin="0s"    repeatCount="indefinite" calcMode="linear"><mpath href="#rp-p1"/></animateMotion></circle>
        <circle r="3.5" fill="#2da88e"><animateMotion dur="1.5s" begin="-0.5s" repeatCount="indefinite" calcMode="linear"><mpath href="#rp-p2"/></animateMotion></circle>
        <circle r="3.5" fill="#2da88e"><animateMotion dur="1.5s" begin="-1.0s" repeatCount="indefinite" calcMode="linear"><mpath href="#rp-p3"/></animateMotion></circle>

        <!-- CHECK destinations -->
        <rect x="420" y="5"   width="172" height="50" rx="8" fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.12)" stroke-width="1"/>
        <text x="506" y="22"  text-anchor="middle" dominant-baseline="middle" fill="rgba(255,255,255,0.9)"  font-family="Inter,sans-serif" font-weight="600" font-size="13">GitHub</text>
        <text x="506" y="40"  text-anchor="middle" dominant-baseline="middle" fill="rgba(194,98,10,0.85)"   font-family="Inter,sans-serif" font-size="11">SARIF · code scanning</text>

        <rect x="420" y="63"  width="172" height="50" rx="8" fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.12)" stroke-width="1"/>
        <text x="506" y="80"  text-anchor="middle" dominant-baseline="middle" fill="rgba(255,255,255,0.9)"  font-family="Inter,sans-serif" font-weight="600" font-size="13">GitLab</text>
        <text x="506" y="98"  text-anchor="middle" dominant-baseline="middle" fill="rgba(194,98,10,0.85)"   font-family="Inter,sans-serif" font-size="11">code quality in MRs</text>

        <rect x="420" y="121" width="172" height="50" rx="8" fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.12)" stroke-width="1"/>
        <text x="506" y="138" text-anchor="middle" dominant-baseline="middle" fill="rgba(255,255,255,0.9)"  font-family="Inter,sans-serif" font-weight="600" font-size="13">Jenkins</text>
        <text x="506" y="156" text-anchor="middle" dominant-baseline="middle" fill="rgba(194,98,10,0.85)"   font-family="Inter,sans-serif" font-size="11">warnings-ng plugin</text>

        <rect x="420" y="179" width="172" height="50" rx="8" fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.12)" stroke-width="1"/>
        <text x="506" y="196" text-anchor="middle" dominant-baseline="middle" fill="rgba(255,255,255,0.9)"  font-family="Inter,sans-serif" font-weight="600" font-size="13">Code Climate</text>
        <text x="506" y="214" text-anchor="middle" dominant-baseline="middle" fill="rgba(194,98,10,0.85)"   font-family="Inter,sans-serif" font-size="11">quality reports</text>

        <!-- section separator -->
        <line x1="20" y1="237" x2="592" y2="237" stroke="rgba(255,255,255,0.07)" stroke-width="1" stroke-dasharray="4 5"/>

        <!-- REPORT destinations -->
        <rect x="420" y="248" width="172" height="50" rx="8" fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.12)" stroke-width="1"/>
        <text x="506" y="265" text-anchor="middle" dominant-baseline="middle" fill="rgba(255,255,255,0.9)"  font-family="Inter,sans-serif" font-weight="600" font-size="13">GitHub</text>
        <text x="506" y="283" text-anchor="middle" dominant-baseline="middle" fill="rgba(45,168,142,0.9)"   font-family="Inter,sans-serif" font-size="11">CycloneDX · dep. graph</text>

        <rect x="420" y="306" width="172" height="50" rx="8" fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.12)" stroke-width="1"/>
        <text x="506" y="323" text-anchor="middle" dominant-baseline="middle" fill="rgba(255,255,255,0.9)"  font-family="Inter,sans-serif" font-weight="600" font-size="13">GitLab</text>
        <text x="506" y="341" text-anchor="middle" dominant-baseline="middle" fill="rgba(45,168,142,0.9)"   font-family="Inter,sans-serif" font-size="11">CycloneDX · dep. scan</text>

        <rect x="420" y="364" width="172" height="50" rx="8" fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.12)" stroke-width="1"/>
        <text x="506" y="381" text-anchor="middle" dominant-baseline="middle" fill="rgba(255,255,255,0.9)"  font-family="Inter,sans-serif" font-weight="600" font-size="13">DependencyTrack</text>
        <text x="506" y="399" text-anchor="middle" dominant-baseline="middle" fill="rgba(45,168,142,0.9)"   font-family="Inter,sans-serif" font-size="11">vulnerability tracking</text>
      </svg>

   .. asciinema:: ../asciicasts/check-ci.cast


.. card:: :material-regular:`bolt;2em` Already using submodules? Migrate in seconds.

   ``dfetch import`` automatically converts **Git submodules and SVN externals** into a dfetch manifest.
   No manual work, no lost history — start benefiting from dfetch's workflow immediately.

   .. button-link:: https://dfetch.rtfd.io/en/latest/manual.html#import
      :color: primary
      :shadow:

      :material-regular:`description;1.2em` Read the migration guide


.. div:: band-mint cta-band

   :material-regular:`rocket_launch;2em;sd-text-primary` **Get started in seconds**

   .. div:: cta-buttons

      .. grid:: 2
         :gutter: 2

         .. grid-item::

            .. button-link:: https://github.com/dfetch-org/dfetch/releases/latest
               :color: primary
               :shadow:
               :expand:

               :material-regular:`download;1.5em` Download

         .. grid-item::

            .. button-link:: https://dfetch.rtfd.io/
               :color: secondary
               :shadow:
               :expand:

               :material-regular:`description;1.5em` Read the docs


.. raw:: html

   <script>
   (function () {
     document.documentElement.classList.add('js');
     var targets = document.querySelectorAll(
       '.how-it-works, .band-tint, .band-mint, .why-dfetch, .sd-card'
     );
     var observer = new IntersectionObserver(function (entries) {
       entries.forEach(function (entry) {
         if (entry.isIntersecting) {
           entry.target.classList.add('is-visible');
           observer.unobserve(entry.target);
         }
       });
     }, { threshold: 0.08 });
     targets.forEach(function (el) { observer.observe(el); });
   })();
   </script>


.. div:: sd-text-left sd-text-muted sd-font-weight-light

    Generated: |today|
