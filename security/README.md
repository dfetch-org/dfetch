# Security

This folder contains the threat models.

They depend on features not yet in a pytm release; install a pinned commit
until an official release is available:

`pip install git+https://github.com/OWASP/pytm.git@279ed14aa13ea8f0b989717812fd4626bfcddf3d`

To update the pin, verify the new commit in the upstream repository and replace
the SHA above.

After this you can generate various reports using:

```bash
python -m security.tm_supply_chain --report security/report_template.md > report.md
python -m security.tm_supply_chain --dfd
python -m security.tm_supply_chain --seq

python -m security.tm_usage --report security/report_template.md > report_usage.md
python -m security.tm_usage --dfd
python -m security.tm_usage --seq
```
