
.. _governance:

Governance
==========

Decision-making
---------------

Dfetch follows a *benevolent dictator* model: the lead maintainer holds final
say on direction, design, and releases. All non-trivial decisions happen
openly in GitHub issues and pull-request discussions, and consensus is
preferred. The maintainer resolves disagreements when discussion does not
converge.

Roles and responsibilities
--------------------------

Lead maintainer
~~~~~~~~~~~~~~~

- Merges pull requests to ``main``
- Cuts releases and publishes to PyPI and GitHub Releases
- Triages issues and sets project direction
- Holds PyPI, GitHub organisation, and release-signing credentials

Contributor
~~~~~~~~~~~

- Opens issues and pull requests following the :ref:`contributing` guide
- Reviews code — anyone may review; maintainer approval gates the merge
- Abides by the project's `Code of Conduct <https://github.com/dfetch-org/dfetch/blob/main/CODE_OF_CONDUCT.md>`_

Access continuity
-----------------

Project assets are held under the **dfetch-org** GitHub organisation rather
than a personal account, so access is not tied to a single individual.

- Additional maintainers can be added through the organisation's *People*
  settings without touching the codebase.
- The PyPI project supports multiple owners; co-owners can be added via the
  PyPI collaborator mechanism.
- If the lead maintainer becomes unavailable, any contributor wishing to step
  up should open an issue to discuss. The project is MIT-licensed, so a
  community fork is always a viable path of last resort.
