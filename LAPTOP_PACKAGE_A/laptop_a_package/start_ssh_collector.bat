@echo off
:: ============================================================
:: AuthSentinel SSH Event Collector — Start Script
:: ============================================================
::
:: This script monitors SSH authentication events on this laptop
:: and forwards them to the TAVIX GUARD backend dashboard.
::
:: Usage:
::   start_ssh_collector.bat [BACKEND_URL] [LABEL]
::
:: Example:
::   start_ssh_collector.bat http://192.168.1.100:8000 LAPTOP-A
::
:: ============================================================

setlocal enabledelayedexpansion

if "%~1"=="" (
    set BACKEND=http://localhost:8000
    set LABEL=LAPTOP-A
) else (
    set BACKEND=%~1
    set LABEL=%~2
    if "!LABEL!"=="" set LABEL=LAPTOP-A
)

echo.
echo ╔════════════════════════════════════════════════╗
echo ║  SSH Event Collector for AuthSentinel          ║
echo ╚════════════════════════════════════════════════╝
echo.
echo Backend:  !BACKEND!
echo Label:    !LABEL!
echo.
echo [INFO] Starting SSH monitor...
echo.

python collector_with_ssh.py --backend !BACKEND! --label !LABEL!

pause
