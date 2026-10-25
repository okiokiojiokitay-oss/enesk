@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 replaycore.py
) else (
    python replaycore.py
)
if errorlevel 1 (
    echo.
    echo Python 3.10+ gerekli. README_TR.md dosyasini oku.
    pause
)
