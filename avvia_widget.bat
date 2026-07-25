@echo off
:: Claude Usage Widget - Launcher per Windows
:: Doppio clic per avviare. La console appare per un istante: e' intrinseco ai .bat.
:: Per l'avvio SENZA alcuna finestra (es. avvio automatico) usare avvia_widget.vbs

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
