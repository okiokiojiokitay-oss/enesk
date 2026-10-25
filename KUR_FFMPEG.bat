@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist ffmpeg.exe (
    echo FFmpeg zaten yuklu: %CD%\ffmpeg.exe
    pause
    exit /b 0
)
echo FFmpeg Windows Essentials indiriliyor. Dosya yaklasik 109 MB.
echo Kaynak: https://www.gyan.dev/ffmpeg/builds/
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; $target = Join-Path (Get-Location).Path 'ffmpeg-download.zip'; $unpack = Join-Path (Get-Location).Path 'ffmpeg-unpack'; try { Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile $target; Expand-Archive -LiteralPath $target -DestinationPath $unpack -Force; $exe=Get-ChildItem -LiteralPath $unpack -Filter 'ffmpeg.exe' -Recurse | Select-Object -First 1; if (-not $exe) { throw 'Arsiv icinde ffmpeg.exe yok' }; Copy-Item -LiteralPath $exe.FullName -Destination (Join-Path (Get-Location).Path 'ffmpeg.exe') -Force; Write-Host 'FFmpeg hazir.' } catch { Write-Host ('HATA: ' + $_.Exception.Message); exit 1 } finally { Remove-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue; Remove-Item -LiteralPath $unpack -Recurse -Force -ErrorAction SilentlyContinue }"
if errorlevel 1 (
    echo Indirme basarisiz. Yukaridaki adresten elle indirip bin\ffmpeg.exe dosyasini buraya kopyala.
) else (
    echo Kurulum tamam.
)
pause
