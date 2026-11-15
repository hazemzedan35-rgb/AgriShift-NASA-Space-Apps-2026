@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
if errorlevel 1 (echo Dependency install failed. Verify Python and internet.&pause&exit /b 1)
start "" /min cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8000/dashboard.html"
python start_agrishift.py
pause
