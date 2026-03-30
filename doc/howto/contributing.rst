

Contribute to Dfetch
====================
Before implementing a feature, please ask one of the maintainers to avoid any unnecessary or double work.
Let other people know through the relevant GitHub issue that you are planning on implementing it.
Also for new features, first create an issue that can be discussed.

After implementing (with tests and documentation) create a PR on Github and let your changes be reviewed.

Virtual Environment
-------------------
Create a virtual environment by double-clicking ``script/create_venv.py`` or by running the following command.
This will install all ``development``, ``test`` and ``docs`` dependencies from ``pyproject.toml``, install
*DFetch* as `editable package <https://pip.pypa.io/en/stable/cli/pip_wheel/?highlight=editable#cmdoption-e>`_
and install all runtime dependencies from ``pyproject.toml``.

.. code-block:: bash

    script/create_venv.py

.. important :: *dfetch* is primarily developed with python 3.13

Running in Github Codespaces
----------------------------
Github codespaces make it possible to edit dfetch directly in the browser in a VSCode instance.
All dependencies are pre-installed and makes it easy to get started.

|CodespacesLink|_

.. |CodespacesLink| image:: https://github.com/codespaces/badge.svg
.. _CodespacesLink: https://codespaces.new/dfetch-org/dfetch

.. tip::

   You can preview the documentation locally by running the ``Serve Docs`` task.
   Codespaces will automatically suggest to open the forwarded port to view the
   changes in your browser.

Running in VSCode
-----------------
To debug or run directly from VSCode create the :ref:`virtual environment`.
Select the python from the virtual environment.
And open the ``dfetch.code-workspace``.

Quality
-------
To avoid any discussion about formatting `black <https://github.com/psf/black>`_ is used as code formatter.
Next to that `isort <https://github.com/PyCQA/isort>`_ is used for sorting the imports.
And `doc8 <https://github.com/pycqa/doc8>`_ is used as rst linter.

`import-linter <https://import-linter.readthedocs.io/>`_ is used to guard the :ref:`architecture` by verifying
that imports between modules respect the C4 layer boundaries. Run it with:

.. code-block:: bash

    lint-imports

Run ``script/check_quality.bat`` (or GitHub will run it for you). Alternatively when using VSCode run the `Check Quality` task from the command palette.

Testing
-------

Unit tests
~~~~~~~~~~
`pytest <https://docs.pytest.org/en/latest/>`_ is used as testing framework. All code contributed should be accompanied with unit tests.
Tests can be found in the ``tests`` folder.

To see coverage, in the virtual environment run ``pytest`` with coverage

.. code-block:: bash

    pytest --cov=dfetch tests

From VSCode all tests can be run from the Test view.

Feature tests
~~~~~~~~~~~~~
Feature tests are used for higher-level integration testing of functionality.
For this `behave <https://behave.readthedocs.io/en/latest/>`_ is used as testing framework.
Features are specified in *Gherkin* in so-called feature files in the ``features`` folder.
The sentences in the feature files, map to steps in the ``features/steps`` folder.

Test can be run directly from the command-line

.. code-block:: bash

    behave features

Alternatively in VSCode run the ``Run all feature tests`` task from the command palette.

To debug these tests, mark the ``Feature:`` or ``Scenario:`` to debug with the ``@wip`` tag
and add run the ``Feature tests (wip)`` debug configuration in VSCode.


Creating documentation
----------------------
Run ``script/create_docs.bat`` and open ``index.html`` in ``doc/_build/html`` to read it.
See `This example <https://pythonhosted.org/an_example_pypi_project/sphinx.html>`_ for documenting the code.
Alternatively in VSCode run the ``Create Docs`` task from the command palette.

Design Guide
~~~~~~~~~~~~

The docs and landing page share a single design system. Follow these tokens
whenever you add new pages, diagrams, or HTML blocks to keep the visual
language consistent.

Colour palette
''''''''''''''

.. palette::

   .. swatch:: #c2620a
      :token: --primary
      :label: Amber Orange
      :usage: CTAs, active borders, diagram start nodes, section pips

   .. swatch:: #a0510a
      :token: --primary-dark
      :label: Amber Dark
      :usage: Hover states, gradient end, button borders

   .. swatch:: #4e7fa0
      :token: --accent
      :label: Slate Blue
      :usage: Decision diamonds, links, secondary badges, note borders

   .. swatch:: #3a6682
      :token: --accent-dark
      :label: Slate Dark
      :usage: Hover states on accent elements, diagram labels

   .. swatch:: #1c1917
      :token: --text
      :label: Near Black
      :usage: Body copy, headings, diagram text

   .. swatch:: #78716c
      :token: --text-muted
      :label: Warm Gray
      :usage: Captions, sub-labels, placeholder text, diagram arrow labels

   .. swatch:: #fef8f0
      :token: --bg-tint
      :label: Warm Cream
      :border: #e7e0d8
      :usage: Alternate section bands, card backgrounds, table headers

   .. swatch:: #eff6fa
      :token: --bg-mint
      :label: Cool Mint
      :border: #e7e0d8
      :usage: Tip/note backgrounds, accent section bands

Typography
''''''''''

.. raw:: html

   <div class="dg-type-grid">

     <div class="dg-type-card">
       <div class="dg-type-header">
         <span class="dg-type-name">Inter</span>
         <span class="dg-type-meta">body · UI · headings</span>
       </div>
       <div class="dg-type-body">
         <div class="dg-type-weights">
           <div class="dg-type-weight-row">
             <span class="dg-weight-label">300</span>
             <span class="dg-weight-sample" style="font-weight:300">Vendor dependencies without the pain</span>
           </div>
           <div class="dg-type-weight-row">
             <span class="dg-weight-label">400</span>
             <span class="dg-weight-sample" style="font-weight:400">Vendor dependencies without the pain</span>
           </div>
           <div class="dg-type-weight-row">
             <span class="dg-weight-label">500</span>
             <span class="dg-weight-sample" style="font-weight:500">Vendor dependencies without the pain</span>
           </div>
           <div class="dg-type-weight-row">
             <span class="dg-weight-label">600</span>
             <span class="dg-weight-sample" style="font-weight:600">Vendor dependencies without the pain</span>
           </div>
           <div class="dg-type-weight-row">
             <span class="dg-weight-label">700</span>
             <span class="dg-weight-sample" style="font-weight:700">Vendor dependencies without the pain</span>
           </div>
           <div class="dg-type-weight-row">
             <span class="dg-weight-label">800</span>
             <span class="dg-weight-sample" style="font-weight:800">Vendor dependencies without the pain</span>
           </div>
         </div>
       </div>
     </div>

     <div class="dg-type-card">
       <div class="dg-type-header">
         <span class="dg-type-name">JetBrains Mono</span>
         <span class="dg-type-meta">code · tokens · CLI</span>
       </div>
       <div class="dg-type-body">
         <div class="dg-type-weights">
           <div class="dg-type-weight-row">
             <span class="dg-weight-label">400</span>
             <span class="dg-weight-sample" style="font-family:'JetBrains Mono',monospace;font-weight:400;font-size:.85rem">dfetch update --force</span>
           </div>
           <div class="dg-type-weight-row">
             <span class="dg-weight-label">500</span>
             <span class="dg-weight-sample" style="font-family:'JetBrains Mono',monospace;font-weight:500;font-size:.85rem">dfetch update --force</span>
           </div>
         </div>
         <p style="font-family:'Inter',sans-serif;font-size:0.7rem;color:#78716c;margin-top:1rem;margin-bottom:0;line-height:1.5">
           Use for: inline code, CLI examples, hex values, token names,
           cheatsheet syntax, diagram labels where monospace is needed.
         </p>
       </div>
     </div>

   </div>

CSS tokens reference
''''''''''''''''''''

Use CSS custom properties rather than raw hex values so changes propagate
everywhere automatically.

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Token
     - Value
     - Use for
   * - ``--primary``
     - :colordot:`#c2620a` ``#c2620a``
     - Primary action colour
   * - ``--primary-dark``
     - :colordot:`#a0510a` ``#a0510a``
     - Hover / pressed state
   * - ``--accent``
     - :colordot:`#4e7fa0` ``#4e7fa0``
     - Secondary / info colour
   * - ``--accent-dark``
     - :colordot:`#3a6682` ``#3a6682``
     - Hover on accent elements
   * - ``--text``
     - :colordot:`#1c1917` ``#1c1917``
     - Body text, headings
   * - ``--text-2``
     - :colordot:`#3d3530` ``#3d3530``
     - Secondary text
   * - ``--text-muted``
     - :colordot:`#78716c` ``#78716c``
     - Captions, labels, placeholders
   * - ``--bg-tint``
     - :colordot:`#fef8f0` ``#fef8f0``
     - Warm section backgrounds
   * - ``--bg-mint``
     - :colordot:`#eff6fa` ``#eff6fa``
     - Cool section backgrounds
   * - ``--border``
     - :colordot:`#e7e0d8` ``#e7e0d8``
     - Card borders, dividers
   * - ``--r`` / ``--r-sm`` / ``--r-lg``
     - 12px / 8px / 20px
     - Border radius (card / badge / hero)
   * - ``--shad-sm`` / ``--shad-md`` / ``--shad-lg``
     - —
     - Box shadow tiers

PlantUML diagrams
'''''''''''''''''

All flow and mindmap diagrams must use the shared skinparam block from
``doc/static/uml/check.puml`` as a template. Key values:

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Element
     - Value
     - Notes
   * - Activity background
     - :colordot:`#ffffff` ``#ffffff``
     - White nodes on transparent canvas
   * - Activity border
     - :colordot:`#c2620a` ``#c2620a`` (``--primary``)
     - 1.5 pt thickness
   * - Diamond background
     - :colordot:`#eff6fa` ``#eff6fa`` (``--bg-mint``)
     - Decision nodes use the cool tint
   * - Diamond border
     - :colordot:`#4e7fa0` ``#4e7fa0`` (``--accent``)
     - Consistent with accent colour
   * - Arrow colour
     - :colordot:`#78716c` ``#78716c`` (``--text-muted``)
     - Keeps arrows from competing with nodes
   * - Start node
     - :colordot:`#c2620a` ``#c2620a`` (``--primary``)
     - Filled amber disc
   * - Partition background
     - :colordot:`#fef8f0` ``#fef8f0`` (``--bg-tint``)
     - Warm cream section bands
   * - Default font
     - :colordot:`#1c1917` Arial, 12 pt, ``#1c1917``
     - Matches ``--text``

Diataxis section colours
''''''''''''''''''''''''

Each of the four Diataxis sections has its own accent colour. These are
applied automatically by ``doc/static/js/diataxis.js``: it adds a CSS class
to ``<body>`` and to the sidebar caption elements so both the top page strip
and the sidebar navigation header reflect the section.

.. palette::
   :columns: 4

   .. swatch:: #c2620a
      :token: --dxt-tutorial
      :label: Tutorials
      :usage: Same as --primary; warm amber for learning-oriented pages

   .. swatch:: #4e7fa0
      :token: --dxt-howto
      :label: How-to Guides
      :usage: Same as --accent; slate blue for task-oriented pages

   .. swatch:: #4a7a62
      :token: --dxt-reference
      :label: Reference
      :usage: Sage green; neutral, precise tone for information pages

   .. swatch:: #7a5a9a
      :token: --dxt-explanation
      :label: Explanation
      :usage: Soft purple; contemplative tone for conceptual pages

To add a new page to a section, add its filename (without ``.rst``) to the
``PAGE_SECTIONS`` map in ``doc/static/js/diataxis.js``.

Releasing
---------

- Bump version number in ``dfetch/__init__.py``.
- Run ``./script/release.py``.
- Double check any feature scenarios for a version number.
- Run all unit / feature tests.
- Re-generate asciicasts using VSCode task (linux/mac).
- Commit all release changes.
- Create pull request & merge to ``main``.
- Create annotated tag on ``main`` and push it:

.. code-block:: bash

    git checkout main
    git pull
    git tag -a '0.12.1' -m "Release version 0.12.1"
    git push --tags

- The ``ci.yml`` job will automatically create a draft release in `GitHub Releases <https://github.com/dfetch-org/dfetch/releases/>`_ with all artifacts.
- Once the release is published, a new package is automatically pushed to `PyPi <https://pypi.org/project/dfetch/>`_.

- After release, add new header to ``CHANGELOG.rst``:

.. code-block:: rst

    Release 0.13.0 (unreleased)
    ====================================
