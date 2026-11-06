$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python Launcher bulunamadı. Python 3.12 kurup yeniden deneyin.'
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw 'Node.js bulunamadı. Node.js 22.12 veya üzeri kurup yeniden deneyin.'
}

py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e .
Push-Location frontend
try { npm install } finally { Pop-Location }
Write-Host 'Kurulum tamamlandı. Geliştirmeyi başlatmak için .\scripts\dev-windows.ps1 çalıştırın.'
