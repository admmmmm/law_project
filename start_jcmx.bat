@echo off
setlocal

set ROOT=%~dp0
set PYTHON=C:\Users\adm14\AppData\Local\Programs\Python\Python310\python.exe

echo.
echo ========================================
echo  JCMX one-click web launcher
echo ========================================
echo.

cd /d "%ROOT%frontend_v2"
echo [1/3] Building frontend_v2 for /jcmx ...
set VITE_BASE_PATH=/jcmx/
call npm.cmd run build
if errorlevel 1 (
  echo frontend_v2 build failed.
  pause
  exit /b 1
)

cd /d "%ROOT%"
echo.
echo [2/3] Starting backend in a visible window ...
start "JCMX Backend :8000" cmd /k "cd /d ""%ROOT%backend"" && ""%PYTHON%"" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo.
echo [3/3] Starting Caddy in a visible window ...
start "JCMX Caddy adm143.xyz" cmd /k "cd /d ""%ROOT%"" && caddy run --config Caddyfile.jcmx"

echo.
echo Started.
echo.
echo Open:
echo   https://adm143.xyz/jcmx/
echo.
echo If a port is already occupied, close the old Backend/Caddy windows and run this file again.
echo.
pause

endlocal
