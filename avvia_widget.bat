@echo off
:: Claude Usage Widget - Launcher per Windows
:: Doppio clic per avviare. La console appare per un istante: e' intrinseco ai .bat.
:: Per l'avvio SENZA alcuna finestra: esegui una volta crea_collegamento_silenzioso.ps1
:: (tasto destro > Esegui con PowerShell) e usa il collegamento .lnk che genera.

title Claude Usage Widget

:: Controlla che Python (pythonw) sia installato — "where" e' istantaneo,
:: non avvia l'interprete come faceva "python --version"
where pythonw >nul 2>&1
if %errorlevel% neq 0 (
    echo Python non trovato.
    echo Scaricalo da https://www.python.org/downloads/
    echo Assicurati di spuntare "Add Python to PATH" durante l'installazione.
    pause
    exit /b 1
)

:: Avvia il widget. Le dipendenze mancanti (requests) le gestisce lo script
:: stesso: auto-install silenzioso, messaggio d'errore se fallisce.
start "" /b pythonw "%~dp0claude_usage.py"
