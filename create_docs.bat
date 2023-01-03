@echo off
setlocal enabledelayedexpansion

cd %~dp0

python create_venv.py --extra_requirements "docs"
if not !ERRORLEVEL! == 0 echo "Something went wrong creating the venv." && exit /b !ERRORLEVEL!

call .\venv\Scripts\activate.bat
.\doc\make.bat html
