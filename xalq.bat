@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo    XALQ Agent Enterprise v1.2.0
echo ========================================
echo.

REM 1. Check for Virtual Environment
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Ativando ambiente virtual (.venv)...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo [INFO] Ativando ambiente virtual (venv)...
    call venv\Scripts\activate.bat
)

REM 2. Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo Por favor, instale o Python 3.10 ou superior e adicione ao PATH.
    pause
    exit /b 1
)

REM 3. Check Dependencies (Quick Check)
python -c "import google.generativeai" >nul 2>&1
if errorlevel 1 (
    echo [AVISO] Dependencias nao encontradas ou incompletas.
    echo Instalando pacotes necessarios...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERRO] Falha na instalacao das dependencias via pip.
        pause
        exit /b 1
    )
    echo [SUCESSO] Dependencias instaladas.
)

REM 4. Launch Application
echo Iniciando XALQ Agent...
echo.
python Xalq.py

if errorlevel 1 (
    echo.
    echo [ERRO] A aplicacao encerrou com erro.
    pause
    exit /b 1
)

echo.
echo Aplicacao encerrada com sucesso.
pause
