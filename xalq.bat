@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo    XALQ Agent Enterprise Launcher
echo ========================================
echo.

REM Tenta usar o Launcher Python que eh mais robusto
python launcher.py

if errorlevel 1 (
    echo.
    echo [ERRO] O launcher falhou.
    pause
    exit /b 1
)
