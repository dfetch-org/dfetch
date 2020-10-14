@echo off
setlocal enabledelayedexpansion

set VENV_DIR=venv
set SRC_DIR=%~dp0

cd %SRC_DIR%

if not exist %VENV_DIR% (
    python create_venv.py --requirements requirements.txt
    if not !ERRORLEVEL! == 0 echo "Something went wrong creating the venv." && exit /b !ERRORLEVEL!
)

call .\venv\Scripts\activate.bat

set PYTHON_MODULE=dfetch tests
set PYLINTRCPATH=.pylintrc
set MYPYINIPATH=.mypy.ini

echo Running pylint and mypy on %PYTHON_MODULE%

if defined JENKINS_URL (
    pylint %PYTHON_MODULE% --rcfile=%PYLINTRCPATH% --output-format=parseable --reports=no > pylint.log
    mypy dfetch --config-file=%MYPYINIPATH% --junit-xml mypy.xml >> pylint.log
    set ERRORLEVEL=0
) else (
    pylint %PYTHON_MODULE% --rcfile=%PYLINTRCPATH% --output-format=colorized
    mypy dfetch --config-file=%MYPYINIPATH%
    pause
)
