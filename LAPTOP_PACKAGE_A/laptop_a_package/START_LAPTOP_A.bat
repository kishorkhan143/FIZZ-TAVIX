@echo off
setlocal

net session >nul 2>&1
if errorlevel 1 goto :admin_required

echo.
echo  AUTH SENTINEL - Laptop A Event Forwarder
echo.
set /p "LAPTOP_B_IP=Enter Laptop B IP address: "
if not defined LAPTOP_B_IP goto :missing_ip
set "BACKEND_URL=http://%LAPTOP_B_IP%:8000"

cd /d "%~dp0"
set "PY_CMD=python"
python --version >nul 2>&1
if errorlevel 1 (
    set "PY_CMD=py"
    py --version >nul 2>&1
    if errorlevel 1 goto :python_missing
)
for /f "delims=" %%V in ('%PY_CMD% --version 2^>^&1') do echo [INFO] Detected Python version: %%V

if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -c "import win32evtlog, requests, dateutil, colorama" >nul 2>&1
    if errorlevel 1 (
        echo [SETUP] Existing venv is not usable; recreating it.
        rmdir /s /q "venv"
        if exist "venv" goto :venv_remove_failed
    )
)

if not exist "venv\Scripts\python.exe" (
    echo [SETUP] Creating Python virtual environment...
    %PY_CMD% -m venv venv
    if errorlevel 1 goto :venv_create_failed
)

echo [SETUP] Installing requirements...
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :pip_failed
venv\Scripts\python.exe -c "import win32evtlog, requests, dateutil, colorama"
if errorlevel 1 goto :dependency_check_failed

echo.
echo [TEST] Checking Laptop B at %BACKEND_URL%/api/health ...
curl.exe --fail --silent --show-error --max-time 5 "%BACKEND_URL%/api/health" >nul
if errorlevel 1 goto :backend_unavailable
echo [OK] Laptop B backend is reachable.

auditpol /set /subcategory:"Logon" /success:enable /failure:enable >nul 2>&1
if errorlevel 1 (
    echo [INFO] Logon subcategory name unavailable; retrying with its GUID.
    auditpol /set /subcategory:"{0CCE9215-69AE-11D9-BED3-505054503030}" /success:enable /failure:enable >nul
    if errorlevel 1 goto :audit_enable_failed
)
echo [OK] Logon success and failure auditing is enabled.

echo.
echo [INFO] Watching for Event IDs 4624 and 4625.
echo [INFO] Forwarding events to %BACKEND_URL%
echo [INFO] Press Ctrl+C to stop.
echo.
venv\Scripts\python.exe collector.py --backend "%BACKEND_URL%" --label "%COMPUTERNAME%" --interval 0.1
set "RC=%errorlevel%"
echo.
echo [INFO] Collector stopped with exit code %RC%.
pause
exit /b %RC%

:admin_required
echo [ERROR] Run START_LAPTOP_A.bat as Administrator.
pause
exit /b 1

:missing_ip
echo [ERROR] Laptop B IP address is required.
pause
exit /b 1

:python_missing
echo [ERROR] Python was not found. Install Python and add it to PATH.
pause
exit /b 1

:venv_remove_failed
echo [ERROR] Could not remove the unusable venv folder.
pause
exit /b 1

:venv_create_failed
echo [ERROR] Failed to create the Python virtual environment.
pause
exit /b 1

:pip_failed
echo [ERROR] Could not install requirements. Check Python and internet access.
pause
exit /b 1

:dependency_check_failed
echo [ERROR] A required Python dependency could not be imported.
pause
exit /b 1

:backend_unavailable
echo [ERROR] Laptop B backend is unavailable.
echo Check that Laptop B backend is running, that setup_firewall.bat was run, and that both laptops are on the same network.
pause
exit /b 1

:audit_enable_failed
echo [ERROR] Could not enable Logon success and failure auditing.
pause
exit /b 1
