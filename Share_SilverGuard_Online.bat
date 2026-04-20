@echo off
echo =======================================
echo Preparing to Share SilverGuard Online...
echo =======================================

echo [1/3] Building the latest frontend...
cd SilverGuard_App\frontend
call npm run build
cd ..\..

echo.
echo [2/3] Starting backend to serve the application...
:: Use start to run backend in a new window so the script can continue
start "SilverGuard Backend (Hosting Frontend)" cmd /k "cd SilverGuard_App\backend && python -m uvicorn main:app"

echo.
echo [3/3] Generating public URL...
echo Please wait, assigning an internet address via Localtunnel...
echo You may need to press enter if it asks to accept the Localtunnel terms.
call npx localtunnel --port 8000

pause
