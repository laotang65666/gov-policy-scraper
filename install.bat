@echo off
chcp 65001 >nul
echo ==============================================
echo   Gov Policy Scraper - Install Dependencies
echo ==============================================
echo.
echo Installing dependencies (first time, ~1-2 min)...
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python -m pip install -r "%~dp0requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple
) else (
    py -m pip install -r "%~dp0requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo ==============================================
echo   Done! Now double-click run.bat to start.
echo ==============================================
echo.
pause
