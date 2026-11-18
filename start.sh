#!/usr/bin/env bash
# macOS / Linux: starts API (8000) and web app (5173). Ctrl+C stops both.
set -e
cd "$(dirname "$0")"
( cd backend && [ -d venv ] || python3 -m venv venv )
( cd backend && . venv/bin/activate && pip install -q -r requirements.txt && uvicorn app.main:app --port 8000 ) &
( cd frontend && { [ -d node_modules ] || npm install --silent; } && npm run dev ) &
wait
