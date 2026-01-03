

Manifest
========
.. automodule:: dfetch.manifest.manifest

Remotes
-------
.. automodule:: dfetch.manifest.remote

Projects
--------
.. automodule:: dfetch.manifest.project

Schema
------

Below an overview of all possible fields on the manifest. The bold items are mandatory.

.. jsonschema::

    :auto_reference:

    $schema: "http://json-schema.org/draft-07/schema#"
    type: object
    required:
      - manifest
    properties:
      manifest:
        description: Top-level manifest object. See :ref:`Manifest` for details.
        type: object
        required:
          - version
          - projects
        properties:
          version:
            type: number

          remotes:
            type: array
            description: >
              List of remote sources. See :ref:`Remotes` for details.
              Each remote must be unique by its name.
            items:
              type: object
              required:
                - name
                - url-base
              properties:
                name:
                  type: string
                  description: A unique name for the remote.
                url-base:
                  type: string
                default:
                  type: boolean
              uniqueItems: true

          projects:
            type: array
            description: >
              List of projects to Dfetch. See :ref:`Projects` for details.
              Each project must be unique by its name.
            items:
              type: object
              required:
                - name
              properties:
                name:
                  type: string
                  description: A unique name for the project.
                dst:
                  description: Destination path to fetch the project to, see :ref:`Destination` for details.
                  type: string
                branch:
                  type: string
                tag:
                  type: string
                revision:
                  type: string
                url:
                  type: string
                repo-path:
                  description: Path within the repository to fetch, see :ref:`Repo-path` for details.
                  type: string
                remote:
                  description: Name of remote to use as base, see :ref:`Remotes` for details.
                  type: string
                patch:
                  type: string
                  description: Patch to apply after fetching see :ref:`Patch`.
                vcs:
                  type: string
                  description: Version control system used by the project. See :ref:`VCS type` for details.
                  enum:
                    - git
                    - svn
                src:
                  type: string
                  description: >
                    Source path within the repository to fetch, see :ref:`Source` for details.
                ignore:
                  type: array
                  description: Files to ignore. See :ref:`Ignore` for details.
                  items:
                    type: string
              uniqueItems: true
