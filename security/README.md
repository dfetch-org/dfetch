# Security

This folder contains the threat models.

They depend on features not yet in a pytm release; install a pinned commit
until an official release is available:

`pip install git+https://github.com/OWASP/pytm.git@279ed14aa13ea8f0b989717812fd4626bfcddf3d`

To update the pin, verify the new commit in the upstream repository and replace
the SHA above.

After this you can generate various reports using:

```bash
python -m security.tm_supply_chain --report security/report_template.rst > doc/explanation/threat_model_supply_chain.rst
python -m security.tm_supply_chain --dfd
python -m security.tm_supply_chain --seq

python -m security.tm_usage --report security/report_template.rst > doc/explanation/threat_model_usage.rst
python -m security.tm_usage --dfd
python -m security.tm_usage --seq
```

## CRA Compliance Track B

The compliance track does not require pytm. Use `--track-b-only` when pytm is
not installed to explicitly opt in to Track-B-only output (otherwise the
command fails fast to avoid silently incomplete artifacts):

```bash
python -m security.compliance \
    --component security/dfetch.component-definition.json \
    --track-b-only \
    --rst > doc/explanation/compliance_track.rst
```

This produces:

- `security/dfetch.component-definition.json` — OSCAL 1.1.2 Component Definition implementing
  prEN 40000-1-4 Security Objectives for dfetch
- `doc/explanation/compliance_track.rst` — human-readable RST (built into the Sphinx docs)

The prEN 40000-1-4 catalog (`security/cra_pren_4000014_oscal_catalog.json`) is committed as a
static artifact derived from the CEN/CLC/JTC 13 WG 9 deep-dive session by Angelo D'Amato
(Vulnir B.V., STAN4CR), 5 March 2026.
