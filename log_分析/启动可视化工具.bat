@echo off
chcp 65001 >nul
echo ======================================
echo   Claude Code 日志可视化工具
echo ======================================
echo.
echo 正在启动服务器...
echo.
cd /d "%~dp0"
python visualizer_server.py
pause
