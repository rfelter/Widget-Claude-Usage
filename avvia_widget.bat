@echo off
:: Claude Usage Widget - Launcher per Windows
:: Doppio clic su questo file per avviare il widget

title Claude Usage Widget

:: Controlla che Python sia installato
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python non trovato.
    echo Scaricalo da https://www.python.org/downloads/
    echo Assicurati di spuntare "Add Python to PATH" durante l'installazione.
    pause
    exit /b 1
)

:: Installa requests se necessario
python -c "import requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installazione dipendenze...
    python -m pip install requests -q
)

:: Avvia il widget
start /b pythonw "%~dp0claude_usage.py"
