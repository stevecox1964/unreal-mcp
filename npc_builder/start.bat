@echo off
echo Starting NPC Builder...
echo.

start "NPC Builder - Backend" cmd /k "cd /d "%~dp0backend" && pip install -r requirements.txt && uvicorn main:app --port 8001 --reload"
start "NPC Builder - Frontend" cmd /k "cd /d "%~dp0frontend" && npm install && npm run dev"

echo.
echo  Backend:   http://localhost:8001
echo  Frontend:  http://localhost:5173
echo  API docs:  http://localhost:8001/docs
