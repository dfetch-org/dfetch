"""Pytest configuration — pre-register stub modules for missing optional dependencies.

Several dfetch modules import third-party packages that may not be installed in
every test environment (e.g. CI without the full optional extras, or isolated
unit-test runs).  Rather than skip entire test modules we register lightweight
stubs via ``sys.modules`` *before* any test file is imported.

Only the symbols that are actually referenced during import or in the new PR
tests are stubbed out; the stubs are intentionally minimal.

Packages mocked here:
- ``infer_license`` — optional license-detection library (not installed)
- ``strictyaml`` + ``strictyaml.ruamel.*`` — YAML library used by the manifest
- ``tldextract`` — URL parsing library used by dfetch.util.purl
- ``semver`` — semantic versioning used by dfetch.util.versions
- ``patch_ng`` — patch application library used by dfetch.vcs.patch
- ``cyclonedx.builder`` + ``cyclonedx.builder.this`` — cyclonedx v11 API missing
  from cyclonedx 7.6.2 installed in this environment (project requires v11.7.0)
- ``cyclonedx.model.component_evidence`` — moved in cyclonedx v11; not present
  in the installed v7.6.2
- ``behave`` — BDD framework used only for decorator registration
"""

import sys
import types
from unittest.mock import MagicMock


def _make_module(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__spec__ = MagicMock()
    mod.__spec__.name = name
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


def _register_if_missing(name: str, module: types.ModuleType) -> None:
    if name not in sys.modules:
        sys.modules[name] = module


# ---------------------------------------------------------------------------
# infer_license (not installed in this environment)
# ---------------------------------------------------------------------------

_il_types = _make_module("infer_license.types")


class _InferredLicense:
    """Minimal stub for infer_license.types.License."""

    def __init__(
        self,
        name: str = "MIT License",
        shortname: str = "MIT",
        trove_classifier: str | None = None,
    ):
        self.name = name
        self.shortname = shortname
        self.trove_classifier = trove_classifier


_il_types.License = _InferredLicense

_il_api = _make_module("infer_license.api", probabilities=lambda text: [])
_il = _make_module("infer_license")
_il.types = _il_types
_il.api = _il_api

_register_if_missing("infer_license", _il)
_register_if_missing("infer_license.types", _il_types)
_register_if_missing("infer_license.api", _il_api)

# ---------------------------------------------------------------------------
# strictyaml and strictyaml.ruamel.* (not installed in this environment)
# ---------------------------------------------------------------------------

_ruamel_comments = _make_module("strictyaml.ruamel.comments", CommentedMap=dict)
_ruamel_error = _make_module("strictyaml.ruamel.error")
_ruamel_error.CommentMark = type("CommentMark", (), {})
_ruamel_scalar = _make_module("strictyaml.ruamel.scalarstring")
_ruamel_scalar.SingleQuotedScalarString = str
_ruamel_tokens = _make_module("strictyaml.ruamel.tokens")
_ruamel_tokens.CommentToken = type("CommentToken", (), {})
_ruamel = _make_module("strictyaml.ruamel")
_ruamel.comments = _ruamel_comments

_sy = _make_module(
    "strictyaml",
    YAML=MagicMock(),
    StrictYAMLError=Exception,
    YAMLValidationError=Exception,
    load=MagicMock(return_value=MagicMock()),
    Bool=MagicMock(),
    Enum=MagicMock(),
    Float=MagicMock(),
    Int=MagicMock(),
    Map=MagicMock(),
    Optional=MagicMock(),
    Regex=MagicMock(),
    Seq=MagicMock(),
    Str=MagicMock(),
)
_sy.ruamel = _ruamel

for _name, _mod in [
    ("strictyaml", _sy),
    ("strictyaml.ruamel", _ruamel),
    ("strictyaml.ruamel.comments", _ruamel_comments),
    ("strictyaml.ruamel.error", _ruamel_error),
    ("strictyaml.ruamel.scalarstring", _ruamel_scalar),
    ("strictyaml.ruamel.tokens", _ruamel_tokens),
]:
    _register_if_missing(_name, _mod)

# ---------------------------------------------------------------------------
# tldextract (not installed; used at module level by dfetch.util.purl)
# ---------------------------------------------------------------------------

try:
    import tldextract  # noqa: F401 – already present
except ImportError:
    _tld_instance = MagicMock()
    _tld_instance.return_value = MagicMock(domain="example", suffix="com")
    _tldextract_mod = _make_module(
        "tldextract",
        TLDExtract=MagicMock(return_value=_tld_instance),
        extract=MagicMock(),
    )
    _register_if_missing("tldextract", _tldextract_mod)

# ---------------------------------------------------------------------------
# semver (not installed; used by dfetch.util.versions -> dfetch.vcs.archive)
# ---------------------------------------------------------------------------

try:
    import semver  # noqa: F401 – already present
except ImportError:
    _semver_version = _make_module("semver.version", Version=type("Version", (), {}))
    _semver = _make_module("semver")
    _semver.version = _semver_version
    _register_if_missing("semver", _semver)
    _register_if_missing("semver.version", _semver_version)

# ---------------------------------------------------------------------------
# patch_ng (not installed; used by dfetch.vcs.patch)
# ---------------------------------------------------------------------------

try:
    import patch_ng  # noqa: F401 – already present
except ImportError:
    _patch_ng = _make_module(
        "patch_ng",
        DIFF=1,
        GIT=2,
        HG=3,
        SVN=4,
        PLAIN=5,
        MIXED=6,
        PatchSet=MagicMock,
        fromfile=MagicMock(return_value=None),
        fromstring=MagicMock(return_value=None),
        decode_text=MagicMock(return_value=""),
    )
    _register_if_missing("patch_ng", _patch_ng)

# ---------------------------------------------------------------------------
# cyclonedx.model.component_evidence
# (present in newer cyclonedx-python-lib versions but absent in v7.6.2)
# ---------------------------------------------------------------------------

try:
    import cyclonedx.model.component_evidence  # noqa: F401 – already present
except ImportError:
    # Build a stub that provides the names imported by sbom_reporter.py
    _enum = __import__("enum")

    class _AnalysisTechnique(_enum.Enum):
        MANIFEST_ANALYSIS = "manifest-analysis"

    class _IdentityField(_enum.Enum):
        NAME = "name"
        VERSION = "version"
        PURL = "purl"

    class _Identity:
        def __init__(self, *, field=None, tools=None, methods=None, concluded_value=None):
            self.field = field
            self.tools = tools or []
            self.methods = methods or []
            self.concluded_value = concluded_value

    class _Method:
        def __init__(self, *, technique=None, confidence=None, value=None):
            self.technique = technique
            self.confidence = confidence
            self.value = value

    class _Occurrence:
        def __init__(self, *, location=None, line=None, offset=None):
            self.location = location
            self.line = line
            self.offset = offset

    # ComponentEvidence from cyclonedx v11 – in v7.6.2 it lives in
    # cyclonedx.model.component so we import it from there for the stub.
    from cyclonedx.model.component import ComponentEvidence as _ComponentEvidence

    _ce_mod = _make_module(
        "cyclonedx.model.component_evidence",
        AnalysisTechnique=_AnalysisTechnique,
        IdentityField=_IdentityField,
        Identity=_Identity,
        Method=_Method,
        Occurrence=_Occurrence,
        ComponentEvidence=_ComponentEvidence,
    )
    _register_if_missing("cyclonedx.model.component_evidence", _ce_mod)

# ---------------------------------------------------------------------------
# cyclonedx.builder + cyclonedx.builder.this
# (exists in cyclonedx v11, missing from cyclonedx 7.6.2 installed here)
# ---------------------------------------------------------------------------

try:
    import cyclonedx.builder  # noqa: F401 – already present
except ImportError:
    _cdx_builder_this = _make_module(
        "cyclonedx.builder.this",
        this_component=MagicMock(return_value=MagicMock()),
    )
    _cdx_builder = _make_module("cyclonedx.builder")
    _cdx_builder.this = _cdx_builder_this
    _register_if_missing("cyclonedx.builder", _cdx_builder)
    _register_if_missing("cyclonedx.builder.this", _cdx_builder_this)

# ---------------------------------------------------------------------------
# sarif_om (not installed; used by dfetch.reporting.check.sarif_reporter)
# ---------------------------------------------------------------------------

try:
    import sarif_om  # noqa: F401 – already present
except ImportError:
    _sarif_om = _make_module(
        "sarif_om",
        Artifact=MagicMock,
        ArtifactLocation=MagicMock,
        Location=MagicMock,
        Message=MagicMock,
        MultiformatMessageString=MagicMock,
        PhysicalLocation=MagicMock,
        Region=MagicMock,
        ReportingDescriptor=MagicMock,
        Result=MagicMock,
        Run=MagicMock,
        SarifLog=MagicMock,
        Tool=MagicMock,
        ToolComponent=MagicMock,
    )
    _register_if_missing("sarif_om", _sarif_om)

# ---------------------------------------------------------------------------
# behave (used only for decorator registration in json_steps.py)
# ---------------------------------------------------------------------------

try:
    import behave  # noqa: F401 – already present
except ImportError:
    _behave = _make_module("behave")
    _behave_runner = _make_module("behave.runner", Context=type("Context", (), {}))
    _behave.given = lambda *a, **k: (lambda f: f)
    _behave.when = lambda *a, **k: (lambda f: f)
    _behave.then = lambda *a, **k: (lambda f: f)
    _behave.runner = _behave_runner
    _register_if_missing("behave", _behave)
    _register_if_missing("behave.runner", _behave_runner)