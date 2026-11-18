@echo off
REM Starts the SpendSense-XAI API (Windows). Double-click this file.
cd /d "%~dp0backend"
if not exist venv ( python -m venv venv )
call venv\Scripts\activate
pip install -r requirements.txt
echo.
echo API starting at http://127.0.0.1:8000  (leave this window open)
uvicorn app.main:app --reload --port 8000
pause
