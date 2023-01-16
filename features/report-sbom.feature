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
                "serialNumber": "urn:uuid:d9287af7-31b2-4a66-b528-21834077ddad",
                "version": 1,
                "dependencies": [
                    {
                        "dependsOn": [],
                        "ref": "2ede03d4-f69f-4777-a6a4-8f1eaa3a2eec"
                    }
                ],
                "metadata": {
                    "timestamp": "2021-12-08T21:34:38.500715+00:00",
                    "tools": [
                        {
                            "vendor": "dfetch-org",
                            "name": "dfetch",
                            "version": "0.7.0"
                        },
                        {
                            "vendor": "CycloneDX",
                            "name": "cyclonedx-python-lib",
                            "version": "3.1.5",
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
                        "bom-ref": "2ede03d4-f69f-4777-a6a4-8f1eaa3a2eec",
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
