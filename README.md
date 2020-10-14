# DFetch

This directory contains the DFetch that can manage dependencies

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
```
python -m venv venv
venv/Scripts/activate
pip install -r requirements.txt
pip install -e .
```

### Quality
Use following tools (will be automated soon)
```
pylint dfetch
mypy --strict dfetch
black dfetch
```

## Creating internal documentation

Run `create_internal_documentation.bat` and open `index.html` in `doc/internal/_build/html` to read it.
See [This example](https://pythonhosted.org/an_example_pypi_project/sphinx.html) for documenting the code.


# Logo
- Logo: [Beagle (3171) - The Noun Project.svg icon from the Noun Project](https://thenounproject.com/icon/3171)
- Date: 7 March 2018
- Author: NATAPON CHANTABUTR
- License: cc0
- Source: [Wikimedia](https://commons.wikimedia.org/wiki/File:Beagle_(3171)_-_The_Noun_Project.svg)
