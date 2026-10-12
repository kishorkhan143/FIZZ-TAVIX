@echo off
:: ============================================================
:: AuthSentinel — Start Backend + Dashboard Frontend
:: ============================================================
echo.
echo ============================================================
echo   Starting AuthSentinel (Backend API + Frontend Dashboard)
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] Starting Backend API on http://localhost:8000 ...
start "AuthSentinel Backend" cmd /k "%~dp0start_backend.bat"

timeout /t 3 /nobreak >nul

echo [2/3] Starting Frontend Dashboard on http://localhost:5173 ...
start "AuthSentinel Frontend" cmd /k "%~dp0start_dashboard.bat"

timeout /t 2 /nobreak >nul

echo [3/3] Opening Dashboard in browser...
start http://localhost:5173

echo.
echo AuthSentinel is running!
echo - Frontend: http://localhost:5173
echo - Backend:  http://localhost:8000
echo.
