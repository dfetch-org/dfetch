.. Dfetch documentation internal

Internal
========
*DFetch* is becoming larger everyday. To give it some structure below a description of the internals.

Glossary
--------

Superproject
    The top-level project that contains the manifest. It defines and
    coordinates all included projects.

Subproject
    A project defined in the manifest that is copied into the
    superproject. Subprojects are managed and updated as part of the
    superproject's configuration.

Remote
    Defines a source repository base URL and a name. Remotes
    allow you to avoid repeating common URL bases for multiple
    projects in a manifest. A single remote may contain multiple
    (sub-)projects to fetch.

Child Manifest
    Some subprojects can themselves contain a manifest. When
    fetching a subproject, dfetch can optionally check these
    child manifests for additional dependencies or recommendations.

Metadata
    A file created by *DFetch* to store some relevant information about
    a subproject.

Architecture
------------
These diagrams are based on `Simon Brown's C4-model`_.

.. _`Simon Brown's C4-model` : https://c4model.com/#CoreDiagrams

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
