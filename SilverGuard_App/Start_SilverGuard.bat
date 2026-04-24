@echo off
echo =========================================
echo Starting SilverGuard App...
echo =========================================

echo [1/2] Starting FastAPI Backend on Port 8000...
start "SilverGuard Backend" cmd /k "cd backend && python -m uvicorn main:app --reload"

echo [2/2] Starting Vite Frontend on Port 5173...
start "SilverGuard Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo =========================================
echo Done! The browser will open automatically.
echo If it doesn't, please visit:
echo http://127.0.0.1:5173
echo =========================================
pause
