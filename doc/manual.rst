

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

.. raw:: html

   <div class="cheatsheet">

     <!-- masthead -->
     <div class="cs-masthead">
       <div class="cs-masthead-brand">
         <span class="cs-logo">df</span>
         <div>
           <div class="cs-masthead-title">Dfetch CLI Cheatsheet</div>
           <div class="cs-masthead-tagline">Vendor dependencies without the pain &nbsp;&middot;&nbsp; <code>dfetch.yaml</code> found automatically</div>
         </div>
       </div>
       <div class="cs-masthead-legend">
         <span class="cs-tok cs-tok-sc">subcommand</span>
         <span class="cs-tok cs-tok-fl">--flag</span>
         <span class="cs-tok cs-tok-ag">&lt;arg&gt;</span>
       </div>
     </div>

     <!-- two-column body -->
     <div class="cs-body">

       <!-- column 1: Foundational + Utilities -->
       <div class="cs-col">

         <div class="cs-section">
           <div class="cs-label cs-l-primary">
             <span class="cs-label-pip"></span>Foundational
             <span class="cs-label-sub">core workflow &middot; daily use</span>
           </div>

           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">init</span></div>
             <div class="cs-dsc">Create a new <code>dfetch.yaml</code> manifest</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">add</span> <span class="cs-ag">&lt;url&gt;</span></div>
             <div class="cs-dsc">Add a dependency, auto-fill defaults</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">add</span> <span class="cs-fl">-i</span> <span class="cs-ag">&lt;url&gt;</span></div>
             <div class="cs-dsc">Add interactively, step-by-step wizard</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">import</span></div>
             <div class="cs-dsc">Migrate from git submodules / SVN externals</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">check</span> <span class="cs-ag">[project]</span></div>
             <div class="cs-dsc">Show dependencies with newer versions available</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">update</span> <span class="cs-ag">[-f] [project]</span></div>
             <div class="cs-dsc">Fetch / update one or all dependencies</div>
           </div>
         </div>

         <div class="cs-section">
           <div class="cs-label cs-l-utility">
             <span class="cs-label-pip"></span>Utilities
             <span class="cs-label-sub">maintenance &middot; setup &middot; validation</span>
           </div>

           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">freeze</span></div>
             <div class="cs-dsc">Pin all dependencies to currently fetched version</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">environment</span></div>
             <div class="cs-dsc">Verify VCS tools and environment setup</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">validate</span></div>
             <div class="cs-dsc">Validate the manifest without fetching</div>
           </div>
         </div>

       </div><!-- /col 1 -->

       <!-- column 2: Patching + CI/CD -->
       <div class="cs-col">

         <div class="cs-section">
           <div class="cs-label cs-l-accent">
             <span class="cs-label-pip"></span>Patching
             <span class="cs-label-sub">local changes &middot; upstream sync</span>
           </div>

           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">diff</span> <span class="cs-ag">[project]</span></div>
             <div class="cs-dsc">Capture local changes as a patch file</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">update-patch</span> <span class="cs-ag">[project]</span></div>
             <div class="cs-dsc">Re-apply patches after upstream version bump</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">format-patch</span> <span class="cs-ag">[project]</span></div>
             <div class="cs-dsc">Export contributor-ready unified diff</div>
           </div>
         </div>

         <div class="cs-section">
           <div class="cs-label cs-l-ci">
             <span class="cs-label-pip"></span>CI / CD Integration
             <span class="cs-label-sub">reports &middot; sbom &middot; security</span>
           </div>

           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">check</span> <span class="cs-fl">--jenkins-json</span></div>
             <div class="cs-dsc">Jenkins-compatible JSON report</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">check</span> <span class="cs-fl">--sarif</span></div>
             <div class="cs-dsc">SARIF (GitHub Advanced Security etc.)</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">check</span> <span class="cs-fl">--code-climate</span></div>
             <div class="cs-dsc">Code Climate / GitLab report</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">report</span></div>
             <div class="cs-dsc">Print a dependency inventory list</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">report</span> <span class="cs-fl">-t</span> <span class="cs-ag">sbom</span></div>
             <div class="cs-dsc">Generate a Software Bill of Materials</div>
           </div>
         </div>

       </div><!-- /col 2 -->

     </div><!-- /cs-body -->

     <div class="cs-footer">
       dfetch.readthedocs.io &nbsp;&middot;&nbsp; github.com/dfetch-org/dfetch
     </div>

   </div>
