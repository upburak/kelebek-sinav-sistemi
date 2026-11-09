# Windows geliştirme ortamı: Python 3.12 veya üzeri bir sürümle .venv kurar.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Get-ProjectPython {
    # Python Launcher (py) her kurulumda bulunmaz; PATH'teki python de kabul edilir.
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($tag in @('-3.12', '-3.13', '-3.14', '-3')) {
            $ok = $false
            try {
                & py $tag -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' 2>$null
                $ok = ($LASTEXITCODE -eq 0)
            } catch { $ok = $false }
            if ($ok) { return @{ Command = 'py'; Arguments = @($tag) } }
        }
    }
    foreach ($name in @('python', 'python3')) {
        if (-not (Get-Command $name -ErrorAction SilentlyContinue)) { continue }
        $ok = $false
        try {
            & $name -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' 2>$null
            $ok = ($LASTEXITCODE -eq 0)
        } catch { $ok = $false }
        if ($ok) { return @{ Command = $name; Arguments = @() } }
    }
    return $null
}

$Interpreter = Get-ProjectPython
if (-not $Interpreter) {
    throw 'Python 3.12 veya üzeri bulunamadı. python.org adresinden Python 3.12+ kurup yeniden deneyin.'
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw 'Node.js bulunamadı. Node.js 22.12 veya üzeri kurup yeniden deneyin.'
}

$VersionArgs = $Interpreter.Arguments + @('-c', 'import sys;print(sys.executable, sys.version.split()[0])')
Write-Host ("Kullanılan Python: " + (& $Interpreter.Command @VersionArgs))

$VenvArgs = $Interpreter.Arguments + @('-m', 'venv', '.venv')
& $Interpreter.Command @VenvArgs
if (-not (Test-Path '.venv\Scripts\python.exe')) { throw 'Sanal ortam (.venv) oluşturulamadı.' }

& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip güncellenemedi.' }
& '.\.venv\Scripts\python.exe' -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw 'Bağımlılıklar kurulamadı.' }

Push-Location frontend
try {
    npm install
    if ($LASTEXITCODE -ne 0) { throw 'Arayüz bağımlılıkları kurulamadı.' }
} finally { Pop-Location }

Write-Host 'Kurulum tamamlandı. Geliştirmeyi başlatmak için .\scripts\dev-windows.ps1 çalıştırın.'
