@echo off
echo Generating 6 failed logons for user "fakeuser" ...
for /l %%i in (1,1,6) do (
    net use \\%COMPUTERNAME%\IPC$ /user:fakeuser WrongPass%%i >nul 2>&1
    timeout /t 1 /nobreak >nul
)
echo Done. The collector should print [FAILURE] lines and the dashboard should show a HIGH REPEATED_FAILURE alert after 5 failures.
pause
