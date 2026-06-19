"""Data classes shared between compliance_data.py and compliance.py."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ApplicableStandard:
    """One standard assessed for applicability to dfetch."""

    name: str
    reference: str
    applies: bool
    scope_note: str
    gap_note: str = ""


@dataclass
class SODocumentation:
    """Prose documentation fields for a Security Objective implementation."""

    description: str = ""
    evidence_hrefs: list[tuple[str, str]] = field(default_factory=list)
    note: str = ""


@dataclass
class SOImplementation:
    """Dfetch's implementation of one prEN 40000-1-4 Security Objective."""

    so_id: str
    ecr_id: str
    controls: list[str] = field(default_factory=list)
    not_applicable: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    status: Literal[
        "implemented", "partially-implemented", "planned", "not-applicable"
    ] = "partially-implemented"
    doc: SODocumentation = field(default_factory=SODocumentation)


@dataclass
class PartIIRequirement:
    """One CRA Annex I Part II requirement (covered by prEN 40000-1-3)."""

    id: str
    ref: str
    text: str
    controls: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    status: Literal[
        "implemented", "partially-implemented", "planned", "not-applicable"
    ] = "partially-implemented"
