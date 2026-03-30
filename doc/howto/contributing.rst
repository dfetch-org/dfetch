

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

.. raw:: html

   <div class="dg-palette">

     <div class="dg-swatch">
       <div class="dg-swatch-color" style="background:#c2620a;"></div>
       <div class="dg-swatch-body">
         <div class="dg-swatch-token">--primary</div>
         <div class="dg-swatch-hex">#c2620a</div>
         <div class="dg-swatch-label">Amber Orange</div>
         <div class="dg-swatch-usage">CTAs, active borders, diagram start nodes, section pips</div>
       </div>
     </div>

     <div class="dg-swatch">
       <div class="dg-swatch-color" style="background:#a0510a;"></div>
       <div class="dg-swatch-body">
         <div class="dg-swatch-token">--primary-dark</div>
         <div class="dg-swatch-hex">#a0510a</div>
         <div class="dg-swatch-label">Amber Dark</div>
         <div class="dg-swatch-usage">Hover states, gradient end, button borders</div>
       </div>
     </div>

     <div class="dg-swatch">
       <div class="dg-swatch-color" style="background:#4e7fa0;"></div>
       <div class="dg-swatch-body">
         <div class="dg-swatch-token">--accent</div>
         <div class="dg-swatch-hex">#4e7fa0</div>
         <div class="dg-swatch-label">Slate Blue</div>
         <div class="dg-swatch-usage">Decision diamonds, links, secondary badges, note borders</div>
       </div>
     </div>

     <div class="dg-swatch">
       <div class="dg-swatch-color" style="background:#3a6682;"></div>
       <div class="dg-swatch-body">
         <div class="dg-swatch-token">--accent-dark</div>
         <div class="dg-swatch-hex">#3a6682</div>
         <div class="dg-swatch-label">Slate Dark</div>
         <div class="dg-swatch-usage">Hover states on accent elements, diagram labels</div>
       </div>
     </div>

     <div class="dg-swatch">
       <div class="dg-swatch-color" style="background:#1c1917;"></div>
       <div class="dg-swatch-body">
         <div class="dg-swatch-token">--text</div>
         <div class="dg-swatch-hex">#1c1917</div>
         <div class="dg-swatch-label">Near Black</div>
         <div class="dg-swatch-usage">Body copy, headings, diagram text</div>
       </div>
     </div>

     <div class="dg-swatch">
       <div class="dg-swatch-color" style="background:#78716c;"></div>
       <div class="dg-swatch-body">
         <div class="dg-swatch-token">--text-muted</div>
         <div class="dg-swatch-hex">#78716c</div>
         <div class="dg-swatch-label">Warm Gray</div>
         <div class="dg-swatch-usage">Captions, sub-labels, placeholder text, diagram arrow labels</div>
       </div>
     </div>

     <div class="dg-swatch">
       <div class="dg-swatch-color" style="background:#fef8f0; border-bottom:1px solid #e7e0d8;"></div>
       <div class="dg-swatch-body">
         <div class="dg-swatch-token">--bg-tint</div>
         <div class="dg-swatch-hex">#fef8f0</div>
         <div class="dg-swatch-label">Warm Cream</div>
         <div class="dg-swatch-usage">Alternate section bands, card backgrounds, table headers</div>
       </div>
     </div>

     <div class="dg-swatch">
       <div class="dg-swatch-color" style="background:#eff6fa; border-bottom:1px solid #e7e0d8;"></div>
       <div class="dg-swatch-body">
         <div class="dg-swatch-token">--bg-mint</div>
         <div class="dg-swatch-hex">#eff6fa</div>
         <div class="dg-swatch-label">Cool Mint</div>
         <div class="dg-swatch-usage">Tip/note backgrounds, accent section bands</div>
       </div>
     </div>

   </div>

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

.. raw:: html

   <table class="dg-tokens">
     <thead>
       <tr>
         <th>Token</th>
         <th>Value</th>
         <th>Use for</th>
       </tr>
     </thead>
     <tbody>
       <tr>
         <td><code>--primary</code></td>
         <td><span class="dg-dot" style="background:#c2620a"></span>#c2620a</td>
         <td>Primary action colour</td>
       </tr>
       <tr>
         <td><code>--primary-dark</code></td>
         <td><span class="dg-dot" style="background:#a0510a"></span>#a0510a</td>
         <td>Hover / pressed state</td>
       </tr>
       <tr>
         <td><code>--accent</code></td>
         <td><span class="dg-dot" style="background:#4e7fa0"></span>#4e7fa0</td>
         <td>Secondary / info colour</td>
       </tr>
       <tr>
         <td><code>--accent-dark</code></td>
         <td><span class="dg-dot" style="background:#3a6682"></span>#3a6682</td>
         <td>Hover on accent elements</td>
       </tr>
       <tr>
         <td><code>--text</code></td>
         <td><span class="dg-dot" style="background:#1c1917"></span>#1c1917</td>
         <td>Body text, headings</td>
       </tr>
       <tr>
         <td><code>--text-2</code></td>
         <td><span class="dg-dot" style="background:#3d3530"></span>#3d3530</td>
         <td>Secondary text</td>
       </tr>
       <tr>
         <td><code>--text-muted</code></td>
         <td><span class="dg-dot" style="background:#78716c"></span>#78716c</td>
         <td>Captions, labels, placeholders</td>
       </tr>
       <tr>
         <td><code>--bg-tint</code></td>
         <td><span class="dg-dot" style="background:#fef8f0;border:1px solid #e7e0d8"></span>#fef8f0</td>
         <td>Warm section backgrounds</td>
       </tr>
       <tr>
         <td><code>--bg-mint</code></td>
         <td><span class="dg-dot" style="background:#eff6fa;border:1px solid #d0e4ef"></span>#eff6fa</td>
         <td>Cool section backgrounds</td>
       </tr>
       <tr>
         <td><code>--border</code></td>
         <td><span class="dg-dot" style="background:#e7e0d8"></span>#e7e0d8</td>
         <td>Card borders, dividers</td>
       </tr>
       <tr>
         <td><code>--r</code> / <code>--r-sm</code> / <code>--r-lg</code></td>
         <td>12px / 8px / 20px</td>
         <td>Border radius (card / badge / hero)</td>
       </tr>
       <tr>
         <td><code>--shad-sm</code> / <code>--shad-md</code> / <code>--shad-lg</code></td>
         <td>—</td>
         <td>Box shadow tiers</td>
       </tr>
     </tbody>
   </table>

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
     - ``#ffffff``
     - White nodes on transparent canvas
   * - Activity border
     - ``#c2620a`` (``--primary``)
     - 1.5 pt thickness
   * - Diamond background
     - ``#eff6fa`` (``--bg-mint``)
     - Decision nodes use the cool tint
   * - Diamond border
     - ``#4e7fa0`` (``--accent``)
     - Consistent with accent colour
   * - Arrow colour
     - ``#78716c`` (``--text-muted``)
     - Keeps arrows from competing with nodes
   * - Start node
     - ``#c2620a`` (``--primary``)
     - Filled amber disc
   * - Partition background
     - ``#fef8f0`` (``--bg-tint``)
     - Warm cream section bands
   * - Default font
     - Arial, 12 pt, ``#1c1917``
     - Matches ``--text``

Diataxis section colours
''''''''''''''''''''''''

Each of the four Diataxis sections has its own accent colour. These are
applied automatically by ``doc/static/js/diataxis.js``: it adds a CSS class
to ``<body>`` and to the sidebar caption elements so both the top page strip
and the sidebar navigation header reflect the section.

.. raw:: html

   <div class="dg-palette" style="grid-template-columns:repeat(4,1fr);">

     <div class="dg-swatch">
       <div class="dg-swatch-color" style="background:#c2620a;"></div>
       <div class="dg-swatch-body">
         <div class="dg-swatch-token">--dxt-tutorial</div>
         <div class="dg-swatch-hex">#c2620a</div>
         <div class="dg-swatch-label">Tutorials</div>
         <div class="dg-swatch-usage">Same as <code>--primary</code>; warm amber for learning-oriented pages</div>
       </div>
     </div>

     <div class="dg-swatch">
       <div class="dg-swatch-color" style="background:#4e7fa0;"></div>
       <div class="dg-swatch-body">
         <div class="dg-swatch-token">--dxt-howto</div>
         <div class="dg-swatch-hex">#4e7fa0</div>
         <div class="dg-swatch-label">How-to Guides</div>
         <div class="dg-swatch-usage">Same as <code>--accent</code>; slate blue for task-oriented pages</div>
       </div>
     </div>

     <div class="dg-swatch">
       <div class="dg-swatch-color" style="background:#4a7a62;"></div>
       <div class="dg-swatch-body">
         <div class="dg-swatch-token">--dxt-reference</div>
         <div class="dg-swatch-hex">#4a7a62</div>
         <div class="dg-swatch-label">Reference</div>
         <div class="dg-swatch-usage">Sage green; neutral, precise tone for information pages</div>
       </div>
     </div>

     <div class="dg-swatch">
       <div class="dg-swatch-color" style="background:#7a5a9a;"></div>
       <div class="dg-swatch-body">
         <div class="dg-swatch-token">--dxt-explanation</div>
         <div class="dg-swatch-hex">#7a5a9a</div>
         <div class="dg-swatch-label">Explanation</div>
         <div class="dg-swatch-usage">Soft purple; contemplative tone for conceptual pages</div>
       </div>
     </div>

   </div>

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
