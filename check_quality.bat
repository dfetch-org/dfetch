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

pre-commit run

pause

exit /b 0
