Feature: Create an CycloneDX sbom

    *Dfetch* can generate a software Bill-of-Materials (SBOM).

    This SBOM lists the components and their supply chain relationships. Downstream
    users of the software can assess the licenses used and potential risk of dependencies.

    The generated SBOM can be used as input for other tools to monitor dependencies.
    The tools track vulnerabilities or can enforce a license policy within an organization.

    Scenario: A fetched project generates a json sbom
        Given the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              projects:
                - name: cpputest
                  url: https://github.com/cpputest/cpputest
                  tag: v3.4
                  src: 'include/CppUTest'
            """
        And all projects are updated
        When I run "dfetch report -t sbom"
        Then the 'report.json' file contains
            """
             {
                "components": [
                    {
                        "bom-ref": "cpputest-v3.4",
                        "evidence": {
                            "identity": [
                                {
                                    "concludedValue": "cpputest",
                                    "field": "name",
                                    "methods": [
                                        {
                                            "confidence": 0.4,
                                            "technique": "manifest-analysis",
                                            "value": "Name as used for project in dfetch.yaml"
                                        }
                                    ],
                                    "tools": [
                                        "dfetch-0.11.0"
                                    ]
                                },
                                {
                                    "concludedValue": "pkg:github/cpputest/cpputest@v3.4#include/CppUTest",
                                    "field": "purl",
                                    "methods": [
                                        {
                                            "confidence": 0.4,
                                            "technique": "manifest-analysis",
                                            "value": "Determined from https://github.com/cpputest/cpputest as used for the project cpputest in dfetch.yaml"
                                        }
                                    ],
                                    "tools": [
                                        "dfetch-0.11.0"
                                    ]
                                },
                                {
                                    "concludedValue": "v3.4",
                                    "field": "version",
                                    "methods": [
                                        {
                                            "confidence": 0.4,
                                            "technique": "manifest-analysis",
                                            "value": "Version as used for project in dfetch.yaml"
                                        }
                                    ],
                                    "tools": [
                                        "dfetch-0.11.0"
                                    ]
                                }
                            ],
                            "licenses": [
                                {
                                    "license": {
                                        "id": "BSD-3-Clause"
                                    }
                                }
                            ],
                            "occurrences": [
                                {
                                    "line": 5,
                                    "location": "dfetch.yaml",
                                    "offset": 13
                                }
                            ]
                        },
                        "externalReferences": [
                            {
                                "type": "vcs",
                                "url": "https://github.com/cpputest/cpputest"
                            }
                        ],
                        "licenses": [
                            {
                                "license": {
                                    "id": "BSD-3-Clause"
                                }
                            }
                        ],
                        "name": "cpputest",
                        "purl": "pkg:github/cpputest/cpputest@v3.4#include/CppUTest",
                        "type": "library",
                        "version": "v3.4"
                    }
                ],
                "dependencies": [
                    {
                        "ref": "cpputest-v3.4"
                    }
                ],
                "metadata": {
                    "timestamp": "2025-10-10T18:28:32.074803+00:00",
                    "tools": {
                        "components": [
                            {
                                "bom-ref": "dfetch-0.11.0",
                                "externalReferences": [
                                    {
                                        "type": "build-system",
                                        "url": "https://github.com/dfetch-org/dfetch/actions"
                                    },
                                    {
                                        "type": "distribution",
                                        "url": "https://pypi.org/project/dfetch/"
                                    },
                                    {
                                        "type": "documentation",
                                        "url": "https://dfetch.readthedocs.io/"
                                    },
                                    {
                                        "type": "issue-tracker",
                                        "url": "https://github.com/dfetch-org/dfetch/issues"
                                    },
                                    {
                                        "type": "license",
                                        "url": "https://github.com/dfetch-org/dfetch/blob/main/LICENSE"
                                    },
                                    {
                                        "type": "release-notes",
                                        "url": "https://github.com/dfetch-org/dfetch/blob/main/CHANGELOG.rst"
                                    },
                                    {
                                        "type": "vcs",
                                        "url": "https://github.com/dfetch-org/dfetch"
                                    },
                                    {
                                        "type": "website",
                                        "url": "https://dfetch-org.github.io/"
                                    }
                                ],
                                "licenses": [
                                    {
                                        "license": {
                                            "acknowledgement": "declared",
                                            "id": "MIT"
                                        }
                                    }
                                ],
                                "name": "dfetch",
                                "supplier": {
                                    "name": "dfetch-org"
                                },
                                "type": "application",
                                "version": "0.11.0"
                            },
                            {
                                "description": "Python library for CycloneDX",
                                "externalReferences": [
                                    {
                                        "type": "build-system",
                                        "url": "https://github.com/CycloneDX/cyclonedx-python-lib/actions"
                                    },
                                    {
                                        "type": "distribution",
                                        "url": "https://pypi.org/project/cyclonedx-python-lib/"
                                    },
                                    {
                                        "type": "documentation",
                                        "url": "https://cyclonedx-python-library.readthedocs.io/"
                                    },
                                    {
                                        "type": "issue-tracker",
                                        "url": "https://github.com/CycloneDX/cyclonedx-python-lib/issues"
                                    },
                                    {
                                        "type": "license",
                                        "url": "https://github.com/CycloneDX/cyclonedx-python-lib/blob/main/LICENSE"
                                    },
                                    {
                                        "type": "release-notes",
                                        "url": "https://github.com/CycloneDX/cyclonedx-python-lib/blob/main/CHANGELOG.md"
                                    },
                                    {
                                        "type": "vcs",
                                        "url": "https://github.com/CycloneDX/cyclonedx-python-lib"
                                    },
                                    {
                                        "type": "website",
                                        "url": "https://github.com/CycloneDX/cyclonedx-python-lib/#readme"
                                    }
                                ],
                                "group": "CycloneDX",
                                "licenses": [
                                    {
                                        "license": {
                                            "acknowledgement": "declared",
                                            "id": "Apache-2.0"
                                        }
                                    }
                                ],
                                "name": "cyclonedx-python-lib",
                                "type": "library",
                                "version": "11.6.0"
                            }
                        ]
                    }
                },
                "serialNumber": "urn:uuid:7621038e-3047-4862-99e7-d637ee9458a9",
                "version": 1,
                "$schema": "http://cyclonedx.org/schema/bom-1.6.schema.json",
                "bomFormat": "CycloneDX",
                "specVersion": "1.6"
            }
            """
