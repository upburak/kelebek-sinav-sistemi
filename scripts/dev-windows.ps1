$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { throw 'Önce .\scripts\setup-windows.ps1 çalıştırın.' }

$env:PYTHONPATH = Join-Path $Root 'backend'
$ApiPort = & $Python (Join-Path $Root 'scripts\choose_api_port.py')
if ($LASTEXITCODE -ne 0) { throw '127.0.0.1 üzerinde boş API portu bulunamadı.' }
$UiPort = if ($env:KELEBEK_UI_PORT) { $env:KELEBEK_UI_PORT } else { '5173' }
$env:KELEBEK_API_PROXY_TARGET = "http://127.0.0.1:$ApiPort"
Write-Host "Kelebek API: http://127.0.0.1:$ApiPort"
Write-Host "Kelebek arayüzü: http://127.0.0.1:$UiPort"
$Backend = Start-Process -FilePath $Python -ArgumentList @('-m', 'flask', '--app', 'kelebek:create_app', 'run', '--host', '127.0.0.1', '--port', "$ApiPort") -WorkingDirectory $Root -PassThru -NoNewWindow
try {
    Set-Location (Join-Path $Root 'frontend')
    npm run dev -- --host 127.0.0.1 --port $UiPort --strictPort
} finally {
    if (-not $Backend.HasExited) { Stop-Process -Id $Backend.Id -Force }
}
