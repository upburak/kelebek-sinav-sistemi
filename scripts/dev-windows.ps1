$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { throw 'Önce .\scripts\setup-windows.ps1 çalıştırın.' }

$env:PYTHONPATH = Join-Path $Root 'backend'
$Backend = Start-Process -FilePath $Python -ArgumentList @('-m', 'flask', '--app', 'kelebek:create_app', 'run', '--host', '127.0.0.1', '--port', '5000') -WorkingDirectory $Root -PassThru -NoNewWindow
try {
    Set-Location (Join-Path $Root 'frontend')
    npm run dev -- --host 127.0.0.1
} finally {
    if (-not $Backend.HasExited) { Stop-Process -Id $Backend.Id -Force }
}
