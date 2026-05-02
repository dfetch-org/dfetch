# Security

This folder contains the threat models. We use some bleeding edge
features and until there is a release please install it manually:

`pip install git+https://github.com/OWASP/pytm.git@master`

After this you can generate various reports using:

```bash
cd security
python -m tm_supply_chain --report report_template.md > report.md
python -m tm_supply_chain --dfd
python -m tm_supply_chain --seq

python -m tm_usage --report report_template.md > report_usage.md
python -m tm_usage --dfd
python -m tm_usage --seq
```
