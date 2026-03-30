
Architecture
============
*DFetch* has grown significantly. Below is a description of its internals.

These diagrams are based on `Simon Brown's C4-model`_.

.. _`Simon Brown's C4-model` : https://c4model.com/#CoreDiagrams

The layer boundaries shown in the diagrams are enforced at development time by
`import-linter <https://import-linter.readthedocs.io/>`_. The contracts are configured in
``pyproject.toml`` under ``[tool.importlinter]``. Run ``lint-imports`` to verify them locally.
Dependencies must remain unidirectional and follow this order:

.. code-block:: text

    dfetch.commands
         ↓
    dfetch.reporting
         ↓
    dfetch.project
         ↓
    dfetch.manifest  (independent of dfetch.vcs)
    dfetch.vcs       (independent of dfetch.manifest)
         ↓
    dfetch.util  (independent of dfetch.log)
    dfetch.log   (independent of dfetch.util)

C1 - Context
''''''''''''
.. uml:: /static/uml/c1_dfetch_context.puml

C2 - Containers
'''''''''''''''
.. uml:: /static/uml/c2_dfetch_containers.puml

C3 - Components
'''''''''''''''

Commands
~~~~~~~~
.. uml:: /static/uml/c3_dfetch_components_commands.puml

Manifest
~~~~~~~~
.. uml:: /static/uml/c3_dfetch_components_manifest.puml

Project
~~~~~~~
.. uml:: /static/uml/c3_dfetch_components_project.puml
