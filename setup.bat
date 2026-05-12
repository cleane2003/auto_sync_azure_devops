@echo off
REM Script de Setup - Azure DevOps Auto Sync
REM Instala dependências e prepara o ambiente

echo.
echo ============================================================
echo  Azure DevOps Auto Sync - Setup
echo ============================================================
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python nao encontrado. Instale Python 3.8+ em https://www.python.org
    pause
    exit /b 1
)

echo [OK] Python encontrado
python --version

REM Instalar pip
echo.
echo Instalando pip...
python -m pip install --upgrade pip

REM Instalar dependências
echo.
echo Instalando dependências...
pip install -r requirements.txt

if errorlevel 1 (
    echo [ERROR] Falha ao instalar dependências
    pause
    exit /b 1
)

echo.
echo [OK] Dependências instaladas
echo.

REM Testar configuração
echo Testando configuracao...
python -c "import config; print('[OK] Configuracao carregada com sucesso')" 

if errorlevel 1 (
    echo [ERROR] Erro ao carregar configuracao. Verifique o arquivo .env
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Setup Concluido!
echo ============================================================
echo.
echo Proximos passos:
echo   1. Execucao manual: python main.py
echo   2. Agendamento: powershell .\scheduler.ps1 -Action Install
echo   3. Consulte README.md para mais detalhes
echo.
pause
