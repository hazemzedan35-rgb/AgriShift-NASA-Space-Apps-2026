@echo off
rem Used by the Start button inside the AgriShift chat (agrishift://start). Starts the server if it is not running.
cd /d "%~dp0"
powershell -NoProfile -Command "try{Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/assistant/api/health -TimeoutSec 2 | Out-Null; exit 0}catch{exit 1}"
if %errorlevel%==0 (start "" http://127.0.0.1:8000/dashboard.html & exit /b 0)
if not exist ".deps_ok" (python -m pip install -q -r requirements.txt && echo ok>.deps_ok)
start "AgriShift server" /min cmd /k python start_agrishift.py
timeout /t 5 >nul
start "" http://127.0.0.1:8000/dashboard.html
