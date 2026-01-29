@echo off
:loop
echo [%date% %time%] Starting interaction loop...
call run_opencode.bat
echo [%date% %time%] Waiting for 5 minutes...
timeout /t 300
goto loop
