@echo off
cd /d "%~dp0\mybot"

:: Log start time
echo [%date% %time%] Starting SonolBot... >> ..\opencode_task.log

:: Run OpenCode
:: Piping prompt to opencode to follow OPENCODE.md instructions
echo "Check for new emails and process them if any. If none, exit." | opencode

echo [%date% %time%] Finished. >> ..\opencode_task.log
