@echo off
REM Starts the SpendSense-XAI web app (Windows). Double-click after start-backend.bat is running.
cd /d "%~dp0frontend"
if not exist node_modules ( call npm install )
echo.
echo Open http://localhost:5173 in your browser  (leave this window open)
call npm run dev
pause
