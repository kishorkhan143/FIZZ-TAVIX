@echo off
:: ============================================================
:: AuthSentinel -- LAPTOP B: Start Backend
:: Run FIRST.  No admin required.
:: ============================================================
setlocal

echo.
echo  +--------------------------------------------------+
echo  ^|     AUTH SENTINEL  --  Backend  (Laptop B)      ^|
echo  +--------------------------------------------------+
echo.

cd /d "%~dp0backend"

if not exist "venv\Scripts\activate.bat" (
    echo [SETUP] Creating Python virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat

echo [SETUP] Checking dependencies...
pip install -r requirements.txt --quiet

:: Detect LAN IP
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /R /C:"IPv4 Address"') do (
    set IP=%%A
    goto :found
)
:found
set IP=%IP: =%

echo.
echo  Laptop B LAN IP : %IP%
echo  Backend API     : http://%IP%:8000
echo  Dashboard URL   : http://%IP%:5173
echo.
echo  -- Give "http://%IP%:8000" to Laptop A for its collector --
echo.
echo [START] Launching FastAPI backend on 0.0.0.0:8000 ...
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8000

pause
