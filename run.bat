@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
    python main.py
) else (
    py main.py
)
