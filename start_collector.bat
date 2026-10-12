@echo off
:: ============================================================
:: AuthSentinel -- LAPTOP B: Start Collector (this machine)
:: Must run as Administrator to read the Security Event Log.
:: ============================================================
setlocal

net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo.
    echo  [!] This script requires Administrator privileges.
    echo      Right-click ^> Run as administrator
    pause
    exit /b 1
)

echo.
echo  +--------------------------------------------------+
echo  ^|   AUTH SENTINEL  --  Collector  (Laptop B)      ^|
echo  +--------------------------------------------------+
echo.

cd /d "%~dp0collector"

if not exist "venv\Scripts\activate.bat" (
    echo [SETUP] Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat

echo [SETUP] Checking dependencies...
pip install -r requirements.txt --quiet

echo.
echo [INFO] This collector watches LAPTOP B's own Security Event Log.
echo [INFO] Events from Laptop A require running the Laptop A collector package.
echo [INFO] Press Ctrl+C to stop.
echo.

python collector.py --backend http://127.0.0.1:8000 --label LAPTOP-B

pause
