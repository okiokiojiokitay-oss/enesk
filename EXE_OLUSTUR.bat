@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo REPLAYCORE - TEK EXE OLUSTURMA
echo =============================
echo.
if not exist "ffmpeg.exe" (
    echo ffmpeg.exe eksik. KUR_FFMPEG.bat calistiriliyor...
    call "KUR_FFMPEG.bat"
)
if not exist "ffmpeg.exe" goto noffmpeg
where py >nul 2>nul
if errorlevel 1 goto nopython
py -3 -m pip install --upgrade pyinstaller
if errorlevel 1 goto error
py -3 -m PyInstaller --clean --noconfirm --onefile --windowed --name ReplayCore --add-binary "ffmpeg.exe;." replaycore.py
if errorlevel 1 goto error
if not exist "dist\ReplayCore.exe" goto error
echo.
echo BASARILI: dist\ReplayCore.exe
echo FFmpeg dosyasi EXE'nin icine eklendi.
echo Bu EXE'yi kullanan bilgisayarda Python / FFmpeg gerekmez.
pause
exit /b 0
:nopython
echo.
echo HATA: Python bu bilgisayarda kurulu degil.
echo Bilgisayarina Python kurmadan build icin NASIL_EXE_OLUSTURULUR.md
echo dosyasindaki GitHub Actions yontemini kullan.
pause
exit /b 1
:noffmpeg
echo.
echo HATA: ffmpeg.exe indirilemedi.
pause
exit /b 1
:error
echo.
echo HATA: EXE olusturulamadi. Yukaridaki hata mesajlarini kontrol et.
pause
exit /b 1
