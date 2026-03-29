

Manual
======

*Dfetch* acts on the projects listed in the :ref:`Manifest`.
Each action is a separate sub-command. Commands are grouped here from the
core day-to-day workflow through patch management and CI/CD integration.
For a step-by-step walkthrough see :doc:`getting_started`.

.. program-output:: dfetch --help
   :shell:

----

Foundational
------------

These five commands cover the complete everyday workflow: create or migrate a
manifest, register new dependencies, check for newer versions upstream, and
fetch them into your repository.

Init
~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: init

.. asciinema:: asciicasts/init.cast

.. automodule:: dfetch.commands.init

Import
~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: import

.. asciinema:: asciicasts/import.cast

.. automodule:: dfetch.commands.import_

Add
~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: add

.. automodule:: dfetch.commands.add

Non-interactive
```````````````

Pass a URL and *Dfetch* fills in sensible defaults (name, destination, default
branch) and appends the entry immediately — no prompts, no confirmation.
Use ``--name``, ``--dst``, ``--version``, ``--src``, and ``--ignore`` to
override individual fields.

.. asciinema:: asciicasts/add.cast

.. scenario-include:: ../features/add-project-through-cli.feature

Interactive
```````````

Pass ``--interactive`` / ``-i`` to be guided step-by-step through every
manifest field.  Pre-fill fields with the flag options above and those prompts
are skipped.  At the end you can optionally run ``dfetch update`` immediately.

.. asciinema:: asciicasts/interactive-add.cast

.. scenario-include:: ../features/interactive-add.feature

Check
~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: check

.. asciinema:: asciicasts/check.cast

.. automodule:: dfetch.commands.check

Update
~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: update

.. asciinema:: asciicasts/update.cast

.. automodule:: dfetch.commands.update

----

Patching
--------

*Dfetch* has a first-class patch workflow. ``dfetch diff`` captures local
changes as numbered patch files that are re-applied automatically on every
``dfetch update``. When a fix is ready to share upstream, ``dfetch
format-patch`` produces a contributor-ready unified diff.

Diff
~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: diff

.. asciinema:: asciicasts/diff.cast

.. automodule:: dfetch.commands.diff

Update patch
~~~~~~~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: update-patch

.. asciinema:: asciicasts/update-patch.cast

.. automodule:: dfetch.commands.update_patch

Format patch
~~~~~~~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: format-patch

.. asciinema:: asciicasts/format-patch.cast

.. automodule:: dfetch.commands.format_patch

----

CI/CD Integration
-----------------

These commands are designed to plug into automated pipelines. Use ``dfetch
check`` report formats to surface stale or vulnerable dependencies in your
existing security toolchain. Use ``dfetch report`` to generate SBOMs and
inventory lists for compliance audits.

Reporting
~~~~~~~~~
.. automodule:: dfetch.reporting.check.reporter

Jenkins reporter
''''''''''''''''
.. automodule:: dfetch.reporting.check.jenkins_reporter

.. asciinema:: asciicasts/check-ci.cast

Sarif reporter
''''''''''''''
.. automodule:: dfetch.reporting.check.sarif_reporter

Code-climate reporter
'''''''''''''''''''''
.. automodule:: dfetch.reporting.check.code_climate_reporter

Report
~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: report

.. asciinema:: asciicasts/report.cast

.. automodule:: dfetch.commands.report

List (default)
''''''''''''''
.. automodule:: dfetch.reporting.stdout_reporter

Software Bill-of-Materials
''''''''''''''''''''''''''
.. automodule:: dfetch.reporting.sbom_reporter

.. asciinema:: asciicasts/sbom.cast

----

Utilities
---------

Supporting commands for day-to-day maintenance: pin all versions to their
current state, verify your environment is correctly set up, and validate a
manifest without running a fetch.

Freeze
~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: freeze

.. asciinema:: asciicasts/freeze.cast

.. automodule:: dfetch.commands.freeze

Environment
~~~~~~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: environment

.. asciinema:: asciicasts/environment.cast

.. automodule:: dfetch.commands.environment

Validate
~~~~~~~~
.. argparse::
   :module: dfetch.__main__
   :func: create_parser
   :prog: dfetch
   :path: validate

.. asciinema:: asciicasts/validate.cast

.. automodule:: dfetch.commands.validate

----

CLI Cheatsheet
--------------

All commands discover ``dfetch.yaml`` automatically by searching up from the
current working directory. *Italicised* arguments are optional.

.. raw:: html

   <div class="cheatsheet">

     <!-- Foundational -->
     <div class="cs-group">
       <div class="cs-header cs-primary">
         <span class="cs-title">Foundational</span>
         <span class="cs-sub">Core workflow &middot; daily use</span>
       </div>
       <table class="cs-table">
         <tr>
           <td class="cs-cmd"><code>dfetch init</code></td>
           <td class="cs-desc">Create a new <code>dfetch.yaml</code> manifest</td>
         </tr>
         <tr>
           <td class="cs-cmd"><code>dfetch add <em>&lt;url&gt;</em></code></td>
           <td class="cs-desc">Add a dependency, auto-fill defaults</td>
         </tr>
         <tr>
           <td class="cs-cmd"><code>dfetch add -i <em>&lt;url&gt;</em></code></td>
           <td class="cs-desc">Add interactively, step-by-step wizard</td>
         </tr>
         <tr>
           <td class="cs-cmd"><code>dfetch import</code></td>
           <td class="cs-desc">Migrate from git submodules / SVN externals</td>
         </tr>
         <tr>
           <td class="cs-cmd"><code>dfetch check <em>[project]</em></code></td>
           <td class="cs-desc">Show dependencies with newer versions available</td>
         </tr>
         <tr>
           <td class="cs-cmd"><code>dfetch update <em>[-f] [project]</em></code></td>
           <td class="cs-desc">Fetch / update one or all dependencies</td>
         </tr>
       </table>
     </div>

     <!-- Patching -->
     <div class="cs-group">
       <div class="cs-header cs-accent">
         <span class="cs-title">Patching</span>
         <span class="cs-sub">Local changes &middot; upstream sync</span>
       </div>
       <table class="cs-table">
         <tr>
           <td class="cs-cmd"><code>dfetch diff <em>[project]</em></code></td>
           <td class="cs-desc">Capture local changes as a patch file</td>
         </tr>
         <tr>
           <td class="cs-cmd"><code>dfetch update-patch <em>[project]</em></code></td>
           <td class="cs-desc">Re-apply patches after upstream version bump</td>
         </tr>
         <tr>
           <td class="cs-cmd"><code>dfetch format-patch <em>[project]</em></code></td>
           <td class="cs-desc">Export contributor-ready unified diff for upstream PR</td>
         </tr>
       </table>
     </div>

     <!-- CI/CD Integration -->
     <div class="cs-group">
       <div class="cs-header cs-dark">
         <span class="cs-title">CI/CD Integration</span>
         <span class="cs-sub">Reports &middot; SBOM &middot; security</span>
       </div>
       <table class="cs-table">
         <tr>
           <td class="cs-cmd"><code>dfetch check --jenkins-json</code></td>
           <td class="cs-desc">Jenkins-compatible JSON report</td>
         </tr>
         <tr>
           <td class="cs-cmd"><code>dfetch check --sarif</code></td>
           <td class="cs-desc">SARIF report (GitHub Advanced Security&nbsp;etc.)</td>
         </tr>
         <tr>
           <td class="cs-cmd"><code>dfetch check --code-climate</code></td>
           <td class="cs-desc">Code Climate / GitLab report</td>
         </tr>
         <tr>
           <td class="cs-cmd"><code>dfetch report</code></td>
           <td class="cs-desc">Print a dependency inventory list</td>
         </tr>
         <tr>
           <td class="cs-cmd"><code>dfetch report -t sbom</code></td>
           <td class="cs-desc">Generate a Software Bill of Materials</td>
         </tr>
       </table>
     </div>

     <!-- Utilities -->
     <div class="cs-group">
       <div class="cs-header cs-muted">
         <span class="cs-title">Utilities</span>
         <span class="cs-sub">Maintenance &middot; setup &middot; validation</span>
       </div>
       <table class="cs-table">
         <tr>
           <td class="cs-cmd"><code>dfetch freeze</code></td>
           <td class="cs-desc">Pin all dependencies to currently fetched version</td>
         </tr>
         <tr>
           <td class="cs-cmd"><code>dfetch environment</code></td>
           <td class="cs-desc">Verify VCS tools and environment setup</td>
         </tr>
         <tr>
           <td class="cs-cmd"><code>dfetch validate</code></td>
           <td class="cs-desc">Validate the manifest without fetching</td>
         </tr>
       </table>
     </div>

   </div>
