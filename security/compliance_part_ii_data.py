"""Static compliance data: CRA Part II software requirements (prEN 40000-1-3).

Split out of compliance_data.py to stay within the 1000-line limit per file.
"""

from security.compliance_types import PartIIRequirement

PART_II_REQUIREMENTS: list[PartIIRequirement] = [
    PartIIRequirement(
        id="pii-01",
        ref="Part II §1",
        text="Identify and document vulnerabilities and components (SBOM).",
        controls=["C-021", "C-022"],
        status="implemented",
    ),
    PartIIRequirement(
        id="pii-02",
        ref="Part II §2",
        text="Address vulnerabilities without delay; provide free security updates.",
        controls=["C-015", "C-016", "SECURITY.md"],
        gaps=[
            "No LTS backport policy (latest release only — documented in SECURITY.md)"
        ],
        status="partially-implemented",
    ),
    PartIIRequirement(
        id="pii-03",
        ref="Part II §3",
        text="Apply effective coordinated vulnerability disclosure (CVD) policy.",
        controls=["SECURITY.md"],
        status="implemented",
    ),
    PartIIRequirement(
        id="pii-04",
        ref="Part II §4",
        text="Report actively exploited vulnerabilities to national CSIRT and ENISA.",
        status="not-applicable",
    ),
    PartIIRequirement(
        id="pii-05",
        ref="Part II §5",
        text="Publish coordinated vulnerability disclosure policy.",
        controls=["SECURITY.md"],
        status="implemented",
    ),
    PartIIRequirement(
        id="pii-06",
        ref="Part II §6",
        text="Share information on vulnerabilities in integrated components.",
        controls=["C-022", "C-016"],
        gaps=["No proactive downstream notification process"],
        status="partially-implemented",
    ),
    PartIIRequirement(
        id="pii-07",
        ref="Part II §7",
        text="Provide security updates free of charge for the support period.",
        controls=["MIT licence", "PyPI", "SECURITY.md"],
        status="implemented",
    ),
]
