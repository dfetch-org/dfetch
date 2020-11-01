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

CALL :sub_display Pylint
pylint dfetch --output-format=colorized

CALL :sub_display isort
isort dfetch

CALL :sub_display black
black dfetch

CALL :sub_display flake8
flake8 dfetch

CALL :sub_display pylint
pylint dfetch

CALL :sub_display mypy
mypy --strict dfetch

CALL :sub_display doc8
doc8 doc

CALL :sub_display pydocstyle
pydocstyle dfetch

CALL :sub_display bandit
bandit -r dfetch

CALL :sub_display radon
radon mi -nb dfetch
radon cc -nb dfetch

pause

exit /b 0

:sub_display
echo.
echo.
echo ############################### %1 #################################
exit /b