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
            {"bomFormat": "CycloneDX", "specVersion": "1.3", "serialNumber": "urn:uuid:d9287af7-31b2-4a66-b528-21834077ddad", "version": 1, "components": [{"type": "library", "name": "cpputest", "version": "v3.4", "purl": "pkg:github/cpputest/cpputest@v3.4", "group": "cpputest", "licenses": [{"license": {"name": "BSD 3-Clause \"New\" or \"Revised\" License"}}]}], "metadata": {"timestamp": "2021-12-08T21:34:38.500715+00:00", "tools": [{"vendor": "CycloneDX", "name": "cyclonedx-python-lib", "version": "0.9.1"}, {"vendor": "dfetch-org", "name": "dfetch", "version": "0.4.0"}]}}
            """
