@echo off
REM Start backend and frontend in separate command windows (Windows)
REM Usage: double-click this file or run from PowerShell/CMD: start_servers.bat

REM Start backend in a new window and keep it open
start "EMS Backend" cmd /k "cd /d %~dp0backend && python run_server.py"

REM Start frontend in a new window and keep it open
start "EMS Frontend" cmd /k "cd /d %~dp07_frontend_dashboard && node server.js"

echo Launched backend and frontend in separate windows.
pause
