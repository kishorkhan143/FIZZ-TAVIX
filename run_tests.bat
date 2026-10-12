@echo off
:: ============================================================
:: AuthSentinel — Run Lab Simulation Tests
:: Use this instead of a real Laptop A if needed.
:: ============================================================

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║  AUTH SENTINEL — Lab Test Simulation         ║
echo  ║  Simulates Laptop A authentication events    ║
echo  ╚══════════════════════════════════════════════╝
echo.

set /p BACKEND="Enter backend URL (default: http://localhost:8000): "
if "%BACKEND%"=="" set BACKEND=http://localhost:8000

python test_simulate.py --backend %BACKEND%

pause
