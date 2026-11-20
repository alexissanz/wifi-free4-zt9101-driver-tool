@echo off
:: ============================================================================
:: INSTALADOR AUTOMÁTICO DE DRIVER USB WI-FI FREE 4 (ZT9101)
:: Execução com Elevação Automática de Administrador
:: ============================================================================
title Instalador USB Wi-Fi Free 4
setlocal EnableDelayedExpansion

:: Verifica privilégios administrativos
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [*] Solicitando permissao de Administrador...
    powershell -NoProfile -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

if exist "Instalador_WiFi_Free4.exe" (
    echo [*] Iniciando instalador compilado standalone...
    "Instalador_WiFi_Free4.exe"
    pause
    exit /b
)

python --version >nul 2>&1
if %errorLevel% equ 0 (
    echo [*] Executando instalador Python...
    python "%~dp0wifi_installer.py"
    pause
    exit /b
)

echo [!] Executando instalacao direta via PnPUtil...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_direct.ps1"
pause
