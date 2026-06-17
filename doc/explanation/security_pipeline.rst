
.. _security-pipeline:

Security Documentation Pipeline
================================

.. note::

  This page explains how the *dfetch* security documentation is produced.
  It is aimed at contributors and maintainers who want to understand or
  regenerate the security artifacts.

The diagram below follows the structure of figure 4.1.2.2 in the
`EU Blue Guide on the implementation of EU product rules (2022) <https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX%3A52022XC0629%2804%29>`_:
all requirements are on the left, a risk-and-threat assessment step (dashed box)
selects which requirements apply, the applicable subset sits in the third column,
and the right side shows two output paths — a solid-arrow path where coverage is
provided by a recognised methodology (STRIDE / pytm), and a dashed-arrow path
where no harmonised standard applies and the requirement is addressed directly as
a documented gap or compliance artefact.

.. uml:: /static/uml/security_doc_flow.puml

**Threat model pipeline** —
`security/tm_supply_chain.py <https://github.com/dfetch-org/dfetch/blob/main/security/tm_supply_chain.py>`_
and
`security/tm_usage.py <https://github.com/dfetch-org/dfetch/blob/main/security/tm_usage.py>`_
define the model elements (actors, data flows, trust boundaries) using the
*pytm* library.
`security/threats.json <https://github.com/dfetch-org/dfetch/blob/main/security/threats.json>`_
provides a catalog of 60+ STRIDE-classified threats.
`security/tm_render.py <https://github.com/dfetch-org/dfetch/blob/main/security/tm_render.py>`_
drives *pytm*, matches threats against model elements, and combines the output
with
`security/report_template.rst <https://github.com/dfetch-org/dfetch/blob/main/security/report_template.rst>`_
to produce the two RST threat-model pages (:doc:`threat_model_supply_chain` and
:doc:`threat_model_usage`), each containing an embedded data-flow diagram, a
sequence diagram, and tables for assets, threats, and controls.

**Compliance pipeline** —
`security/tm_controls_data.py <https://github.com/dfetch-org/dfetch/blob/main/security/tm_controls_data.py>`_
defines all dfetch controls (Track A: risk-driven; Track B: compliance-only controls
in ``compliance_data.py``) and their mapping to CRA essential requirements
and prEN 40000-1-4 security objectives.
`security/compliance.py <https://github.com/dfetch-org/dfetch/blob/main/security/compliance.py>`_
reads those definitions together with the static OSCAL catalog and generates
:doc:`compliance_track` (human-readable RST mapping tables),
:doc:`control_register` (the full control register with GitHub references), and
`security/dfetch.component-definition.json <https://github.com/dfetch-org/dfetch/blob/main/security/dfetch.component-definition.json>`_
(machine-readable OSCAL 1.2.2 Component Definition). The Component Definition
includes the supplier party, component purpose, and ``evidence`` links on each
implemented-requirement pointing to the concrete code or CI file that implements
the control — making the mapping machine-verifiable.

**Release attestations** — GitHub Actions generates five cryptographic attestation
types *about dfetch itself* during every release, signed by Sigstore and verifiable
by consumers with ``gh attestation verify`` (see :ref:`verify-integrity`):
CycloneDX SBOM (composition of the published package), SLSA Build Provenance
(source-to-binary traceability), SLSA Source Provenance (governance controls on
``main``), Verification Summary Attestation (VSA), and in-toto Test Results
(CI test suite passed before any binary was produced).  These are required by
supply-chain controls :ref:`C-026 <c-026>`, :ref:`C-037 <c-037>`,
:ref:`C-039 <c-039>`, and :ref:`C-040 <c-040>`.

**Dependency-scanning outputs** — When users run ``dfetch check``, the reporting
layer emits findings about outdated or missing vendored dependencies in the format
of their choice:
:ref:`SARIF <check-ci-github>` (for GitHub code scanning),
:ref:`Code Climate JSON <check-ci-gitlab>` (GitLab merge-request quality reports), or
:ref:`Jenkins JSON <check-ci-jenkins>` (Jenkins warnings-ng plugin).

**Artifacts at a glance**

.. list-table::
   :header-rows: 1
   :widths: 40 15 45

   * - Artifact
     - Type
     - Purpose

   * - :doc:`threat_model_supply_chain`
     - RST (generated)
     - Supply-chain threat model: DFD, sequence diagram, STRIDE tables, controls

   * - :doc:`threat_model_usage`
     - RST (generated)
     - Runtime threat model: DFD, sequence diagram, STRIDE tables, controls

   * - :doc:`compliance_track`
     - RST (generated)
     - CRA Annex I → prEN 40000-1-4 SO.* → dfetch control traceability tables

   * - :doc:`control_register`
     - RST (generated)
     - All dfetch controls with type, references, and status

   * - `security/dfetch.component-definition.json <https://github.com/dfetch-org/dfetch/blob/main/security/dfetch.component-definition.json>`_
     - OSCAL 1.2.2 JSON (generated)
     - Machine-readable Component Definition; maps dfetch controls to CRA ECRs;
       includes supplier party, component purpose, and evidence links to code

   * - `security/cra_pren_4000014_oscal_catalog.json <https://github.com/dfetch-org/dfetch/blob/main/security/cra_pren_4000014_oscal_catalog.json>`_
     - OSCAL 1.2.2 JSON (static)
     - Static prEN 40000-1-4 catalog; includes parties, roles, and responsible-parties

   * - :ref:`Release attestations <verify-integrity>`
     - Sigstore-signed (GitHub Actions)
     - Five attestation types generated *about dfetch* on every release: CycloneDX
       SBOM, SLSA Build Provenance, SLSA Source Provenance, VSA, in-toto Test Results.
       Required by controls :ref:`C-026 <c-026>`, :ref:`C-037 <c-037>`,
       :ref:`C-039 <c-039>`, :ref:`C-040 <c-040>`;
       verifiable with ``gh attestation verify``.

   * - :ref:`SARIF output <check-ci-github>`
     - JSON (SARIF 2.1.0)
     - ``dfetch check --output-type sarif``; upload to GitHub code scanning

   * - :ref:`Code Climate JSON <check-ci-gitlab>`
     - JSON (Code Climate)
     - ``dfetch check --output-type code-climate``; GitLab MR quality widget

   * - :ref:`Jenkins JSON <check-ci-jenkins>`
     - JSON
     - ``dfetch check --output-type jenkins``; Jenkins warnings-ng plugin
