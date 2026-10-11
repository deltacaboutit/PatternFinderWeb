@echo off
setlocal
cd /d "%~dp0"
title Pattern Finder (phone version) running on this PC

REM ------------------------------------------------------------------
REM  OPTIONAL. Runs the phone version on this Windows PC, so you can try
REM  it before putting it online. Your iPhone can open it too, as long
REM  as it is on the same Wi-Fi: use the "Network URL" shown below.
REM  Keep this window open while you use the app. Close it to stop.
REM ------------------------------------------------------------------

if exist ".venv\setup_done.txt" goto run

echo First-time setup: installing what the app needs. Please wait...
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY goto nopython
%PY% -c "import sys" >nul 2>nul || goto nopython
if not exist ".venv\Scripts\python.exe" (
    %PY% -m venv .venv || goto failed
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto failed
echo done> ".venv\setup_done.txt"

:run
echo.
echo  Starting... A browser tab will open. On your iPhone, type the
echo  "Network URL" shown below into Safari (same Wi-Fi only).
echo.
".venv\Scripts\python.exe" -m streamlit run streamlit_app.py --server.headless false
pause
exit /b 0

:nopython
echo.
echo  Python was not found. Install it from https://www.python.org/downloads/windows/
echo  and tick "Add python.exe to PATH" on the first screen. Then run this file again.
pause
exit /b 1

:failed
echo.
echo  Setup did not finish. Check your internet connection and try again.
pause
exit /b 1
