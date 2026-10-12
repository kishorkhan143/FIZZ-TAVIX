@echo off
:: ============================================================
:: AuthSentinel -- Open firewall ports for LAN access
:: Run as Administrator ONCE before the demo
:: ============================================================

net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [!] Run this script as Administrator.
    pause
    exit /b 1
)

echo.
echo [SETUP] Opening AuthSentinel firewall ports...

netsh advfirewall firewall delete rule name="AuthSentinel Backend" >nul 2>&1
netsh advfirewall firewall delete rule name="AuthSentinel Dashboard" >nul 2>&1

netsh advfirewall firewall add rule name="AuthSentinel Backend" dir=in action=allow protocol=TCP localport=8000 profile=any
netsh advfirewall firewall add rule name="AuthSentinel Dashboard" dir=in action=allow protocol=TCP localport=5173 profile=any
netsh advfirewall firewall add rule name="AuthSentinel Ping ICMP" dir=in action=allow protocol=icmpv4:8,any profile=any
powershell -Command "Set-NetConnectionProfile -InterfaceAlias 'Wi-Fi' -NetworkCategory Private" >nul 2>&1

echo.
echo [DONE] Firewall rules added:
echo   Port 8000 (Backend API + WebSocket) - open for LAN
echo   Port 5173 (React Dashboard)         - open for LAN
echo.

:: Show the LAN IP
echo [INFO] This machine's WiFi IP (Laptop B IP):
ipconfig | findstr /C:"IPv4"

echo.
echo Give the IP above to Laptop A.
echo Laptop A should use:  http://^<this IP^>:8000
echo.
pause
