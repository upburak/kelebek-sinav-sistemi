# Windows x64 için uygulama klasörü ve (Inno Setup kuruluysa) kurulum paketi üretir. Çıktı: dist\
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  # Ortam kurulumu tek yerde: setup betiği Python Launcher'ı olmayan bilgisayarlarda
  # PATH'teki Python 3.12+ sürümünü de bulur.
  & (Join-Path $PSScriptRoot "setup-windows.ps1")
  if (-not (Test-Path ".venv\Scripts\python.exe")) { throw "Sanal ortam (.venv) kurulamadı." }
}
$Python = Join-Path $Root ".venv\Scripts\python.exe"
& $Python -m pip install --quiet "pyinstaller>=6.10,<7"
npm --prefix frontend ci
npm --prefix frontend run build

$env:PYTHONPATH = "backend"
& $Python -m unittest discover -s backend/tests
if ($LASTEXITCODE -ne 0) { throw "Testler başarısız." }
& $Python -m PyInstaller --noconfirm --clean --distpath dist --workpath build packaging/kelebek.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller başarısız." }

$Version = & $Python -c "from kelebek.version import APP_VERSION;print(APP_VERSION)"
$Zip = "dist\KelebekSinavSistemi-$Version-windows-x64.zip"
if (Test-Path $Zip) { Remove-Item $Zip }
Compress-Archive -Path "dist\KelebekSinavSistemi\*" -DestinationPath $Zip

$Iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
if (-not $Iscc) { $Iscc = Get-Item "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" -ErrorAction SilentlyContinue }
if ($Iscc) {
  & $Iscc.Source "/DAppVersion=$Version" "packaging\windows\kelebek.iss"
} else {
  Write-Host "Inno Setup bulunamadı; yalnızca ZIP paketi üretildi."
}
Get-ChildItem dist -File | ForEach-Object { (Get-FileHash $_.FullName -Algorithm SHA256).Hash + "  " + $_.Name } | Set-Content dist\SHA256SUMS.txt
Write-Host "Hazır: dist\"
