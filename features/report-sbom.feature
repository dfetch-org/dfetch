Feature: Create an CycloneDX sbom

    *Dfetch* can generate a software Bill-of-Materials (SBOM).

    An SBOM lists the components and their supply chain relationships. Downstream
    users of the software can assess the licenses used and potential risk of dependencies.

    The generated SBOM can be used as input for other tools to monitor dependencies.
    The tools track vulnerabilities or can enforce a license policy within an organization.

    Scenario: An fetched project generates a json sbom
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
                "$schema": "http://cyclonedx.org/schema/bom-1.6.schema.json",
                "bomFormat": "CycloneDX",
                "specVersion": "1.6",
                "serialNumber": "urn:uuid:3ce78767-c202-4beb-935e-67f539cf3a58",
                "version": 1,
                "dependencies": [
                    {
                        "ref": "BomRef.7805091949677974.3172811758515278"
                    }
                ],
                "metadata": {
                    "timestamp": "2025-10-03T20:56:03.645362+00:00",
                    "tools": [
                        {
                            "vendor": "dfetch-org",
                            "name": "dfetch",
                            "version": "0.10.0"
                        },
                        {
                            "vendor": "CycloneDX",
                            "name": "cyclonedx-python-lib",
                            "version": "11.1.0",
                            "externalReferences": [
                                {
                                    "url": "https://pypi.org/project/cyclonedx-python-lib/",
                                    "type": "distribution"
                                },
                                {
                                    "url": "https://github.com/CycloneDX/cyclonedx-python-lib/#readme",
                                    "type": "website"
                                },
                                {
                                    "url": "https://github.com/CycloneDX/cyclonedx-python-lib/actions",
                                    "type": "build-system"
                                },
                                {
                                    "url": "https://github.com/CycloneDX/cyclonedx-python-lib/blob/main/LICENSE",
                                    "type": "license"
                                },
                                {
                                    "url": "https://github.com/CycloneDX/cyclonedx-python-lib/blob/main/CHANGELOG.md",
                                    "type": "release-notes"
                                },
                                {
                                    "url": "https://cyclonedx-python-library.readthedocs.io/",
                                    "type": "documentation"
                                },
                                {
                                    "url": "https://github.com/CycloneDX/cyclonedx-python-lib/issues",
                                    "type": "issue-tracker"
                                },
                                {
                                    "url": "https://github.com/CycloneDX/cyclonedx-python-lib",
                                    "type": "vcs"
                                }
                            ]
                        }
                    ]
                },
                "components": [
                    {
                        "type": "library",
                        "bom-ref": "BomRef.7805091949677974.3172811758515278",
                        "name": "cpputest",
                        "version": "v3.4",
                        "externalReferences": [
                            {
                                "type": "vcs",
                                "url": "https://github.com/cpputest/cpputest"
                            }
                        ],
                        "licenses": [
                            {
                                "expression": "BSD 3-Clause \"New\" or \"Revised\" License"
                            }
                        ],
                        "purl": "pkg:github/cpputest/cpputest@v3.4#include/CppUTest"
                    }
                ]
            }
            """
