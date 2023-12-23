Feature: Create an CycloneDX sbom

    *Dfetch* can generate a software Bill-of-Materials (SBOM).

    An SBOM lists the components and their supply chain relationships. Downstream
    users of the software can assess the licenses used and potential risk of dependencies.

    The generated SBOM can be used as input for other tools to monitor dependencies.
    The tools track vulnerabilities or can enforce a license policy within an organization.

    Scenario: An fetched project generates an sbom
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
                "$schema": "http://cyclonedx.org/schema/bom-1.4.schema.json",
                "bomFormat": "CycloneDX",
                "specVersion": "1.4",
                "serialNumber": "urn:uuid:e989dc42-a199-4fe4-87f1-2b7f7a5f48cf",
                "version": 1,
                "dependencies": [
                    {
                        "ref": "a3aff0d8-2f40-4482-bded-577466c0bde9"
                    }
                ],
                "metadata": {
                    "timestamp": "2023-03-25T19:15:03.697694+00:00",
                    "tools": [
                        {
                            "vendor": "dfetch-org",
                            "name": "dfetch",
                            "version": "0.8.0"
                        },
                        {
                            "vendor": "CycloneDX",
                            "name": "cyclonedx-python-lib",
                            "version": "4.2.2",
                            "externalReferences": [
                                {
                                    "url": "https://pypi.org/project/cyclonedx-python-lib/",
                                    "type": "distribution"
                                },
                                {
                                    "url": "https://cyclonedx.org",
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
                                    "url": "https://cyclonedx.github.io/cyclonedx-python-lib/",
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
                        "bom-ref": "a3aff0d8-2f40-4482-bded-577466c0bde9",
                        "name": "cpputest",
                        "version": "v3.4",
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
