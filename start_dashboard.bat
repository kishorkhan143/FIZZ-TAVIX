@echo off
:: ============================================================
:: AuthSentinel — Laptop B: Start Dashboard (React Frontend)
:: ============================================================

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   AUTH SENTINEL — Dashboard Startup      ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo [SETUP] Installing npm dependencies...
    npm install
)

echo.
echo [INFO] Starting dashboard dev server on port 5173...
echo [INFO] Open browser to: http://localhost:5173
echo [INFO] From Laptop A, open: http://LAPTOP-B-IP:5173
echo.
npm run dev

pause
