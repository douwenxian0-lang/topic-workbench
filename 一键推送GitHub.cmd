@echo off
title Push topic-workbench to GitHub
cd /d "%~dp0"
echo.
echo  ============================================
echo   topic-workbench - one-click push to GitHub
echo   If auth is needed, a XXXX-XXXX code will
echo   appear and the device page opens in browser
echo  ============================================
echo.
set PYTHONIOENCODING=utf-8
python "%~dp0setup_and_push.py"
echo.
echo  Press any key to close...
pause >nul
