# DFetch

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/431474d43db0420a92ebc10c1886df8d)](https://app.codacy.com/gh/dfetch-org/dfetch?utm_source=github.com&utm_medium=referral&utm_content=dfetch-org/dfetch&utm_campaign=Badge_Grade)
[![Documentation Status](https://readthedocs.org/projects/dfetch/badge/?version=latest)](https://dfetch.readthedocs.io/en/latest/?badge=latest)
[![Build](https://github.com/dfetch-org/dfetch/workflows/Test/badge.svg)](https://github.com/dfetch-org/dfetch/actions)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![GitHub](https://img.shields.io/github/license/dfetch-org/dfetch)

DFetch can manage dependencies

[![asciicast](https://asciinema.org/a/X7RIrLtctOPBq2ekHr9DyVrRe.png)](https://asciinema.org/a/X7RIrLtctOPBq2ekHr9DyVrRe)

## Running in VSCode

Make sure the venv is created (by using `start_gui.bat` for instance) and set the `venv` as python interpreter.

```json
    "configurations": [
        {
            "name": "Python: Module",
            "type": "python",
            "request": "launch",
            "module": "dfetch.main",
            "justMyCode": false,
            "args": ["update"]
        }
    ]
```

## Contributing

### Setup environment
```bash
python -m venv venv
venv/Scripts/activate
pip install -r requirements.txt
pip install -e .
```

### Quality
Run `check_quality.bat` (or Github will run it for you).

### Creating documentation
Run `create_docs.bat` and open `index.html` in `doc/_build/html` to read it.
See [This example](https://pythonhosted.org/an_example_pypi_project/sphinx.html) for documenting the code.

## Logo
-   Logo: [Beagle (3171) - The Noun Project.svg icon from the Noun Project](https://thenounproject.com/icon/3171)
-   Date: 7 March 2018
-   Author: NATAPON CHANTABUTR
-   License: cc0
-   Source: [Wikimedia](https://commons.wikimedia.org/wiki/File:Beagle_(3171)_-_The_Noun_Project.svg)
