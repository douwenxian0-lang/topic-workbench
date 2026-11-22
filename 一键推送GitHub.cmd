@echo off
chcp 65001 >nul
title 推送到 GitHub - 选题工作台
cd /d "%~dp0"
echo.
echo  ============================================
echo   选题工作台 - 一键推送到 GitHub
echo   需要时会在浏览器里让你点一次 Authorize
echo  ============================================
echo.
python "%~dp0setup_and_push.py"
echo.
echo  按任意键关闭...
pause >nul
