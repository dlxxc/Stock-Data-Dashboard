@echo off
setlocal

set "PORT=8003"
set "URL=http://127.0.0.1:%PORT%/"
set "BACKEND_DIR=%~dp0backend"

title A-Share Dashboard Launcher
echo.
echo ============================================
echo   A-Share Dashboard Launcher
echo ============================================
echo.

netstat -ano | findstr ":%PORT%" | findstr "LISTENING" >nul
if not errorlevel 1 goto :PORTUSED

if not exist "%~dp0frontend\dist\index.html" goto :NODIST
goto :START

:NODIST
echo [WARNING] frontend\dist\index.html not found.
echo           Run 'pnpm build' in frontend first.
echo.

:START
echo [INFO] Starting backend at %URL%
echo        Browser will open in about 3 seconds.
echo.
start "" /min powershell -NoProfile -Command "Start-Sleep -Seconds 3; Start-Process '%URL%'"

pushd "%BACKEND_DIR%"
call ..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port %PORT% --log-level info
set "UVICORN_EXIT=%errorlevel%"
popd

echo.
echo [STOPPED] Backend exited with code %UVICORN_EXIT%.
endlocal
pause
exit /b 0

:PORTUSED
echo.
echo [ERROR] Port %PORT% is already in use.
echo         Close the conflicting process, or change PORT
echo         at the top of this file and in backend\config.py
echo.
pause
exit /b 1