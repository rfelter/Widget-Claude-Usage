# Claude Usage Widget - Genera un collegamento di avvio SENZA alcuna finestra
#
# Perché questo script e non un .vbs pronto all'uso: l'associazione file .vbs
# non è affidabile su tutte le installazioni Windows (VBScript è in fase di
# deprecazione da Microsoft e su alcuni PC il doppio clic su .vbs non apre
# nulla). Un collegamento .lnk puntato direttamente a pythonw.exe evita del
# tutto il problema: Explorer lo esegue nativamente, senza bisogno di alcuna
# associazione di tipo file.
#
# Uso: tasto destro su questo file -> "Esegui con PowerShell" (una tantum).
# Crea "Avvia Widget (silenzioso).lnk" in questa stessa cartella. Il
# collegamento risultante puoi copiarlo su Desktop o in shell:startup
# (Win+R -> shell:startup) per l'avvio automatico.

$ErrorActionPreference = "Stop"

$pyw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pyw) {
    Write-Host "ERRORE: pythonw.exe non trovato nel PATH." -ForegroundColor Red
    Write-Host "Installa Python da https://python.org (spunta 'Add Python to PATH') e riprova."
    Read-Host "Premi Invio per chiudere"
    exit 1
}

$scriptDir = $PSScriptRoot
$target    = Join-Path $scriptDir "claude_usage.py"
if (-not (Test-Path $target)) {
    Write-Host "ERRORE: claude_usage.py non trovato in $scriptDir" -ForegroundColor Red
    Read-Host "Premi Invio per chiudere"
    exit 1
}

$lnkPath = Join-Path $scriptDir "Avvia Widget (silenzioso).lnk"
$wsh = New-Object -ComObject WScript.Shell
$sc  = $wsh.CreateShortcut($lnkPath)
$sc.TargetPath       = $pyw
$sc.Arguments        = "`"$target`""
$sc.WorkingDirectory = $scriptDir
$sc.Description      = "Avvia Claude Usage Widget senza alcuna finestra"
$sc.Save()

Write-Host "Creato: $lnkPath" -ForegroundColor Green
Write-Host "Puoi copiarlo su Desktop o in shell:startup per l'avvio automatico."
Read-Host "Premi Invio per chiudere"
