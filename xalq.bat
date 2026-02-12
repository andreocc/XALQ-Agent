@echo off
REM XALQ Agent - Processador de Relatorios
REM Inicia a aplicacao XALQ Agent

echo ========================================
echo    XALQ Agent - Processador de Relatorios
echo ========================================
echo.

REM Verifica se Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo Por favor, instale o Python 3.8 ou superior.
    pause
    exit /b 1
)

REM Verifica se o arquivo Xalq.py existe
if not exist "Xalq.py" (
    echo [ERRO] Arquivo Xalq.py nao encontrado!
    echo Certifique-se de estar no diretorio correto.
    pause
    exit /b 1
)

echo Iniciando XALQ Agent...
echo.

REM Executa a aplicacao
python Xalq.py

REM Captura codigo de saida
if errorlevel 1 (
    echo.
    echo [ERRO] A aplicacao encerrou com erro.
    pause
    exit /b 1
)

echo.
echo Aplicacao encerrada com sucesso.
