# Menjalankan NutriKos memakai interpreter yang tersedia tanpa mengubah Python sistem.
$ErrorActionPreference = 'Stop'
$projectDir = $PSScriptRoot
Set-Location -LiteralPath $projectDir

if (Get-Command uv -ErrorAction SilentlyContinue) {
    $env:UV_CACHE_DIR = Join-Path $env:TEMP 'NutriKos-uv-cache'
    $pythonExe = (& uv python find --no-python-downloads | Select-Object -Last 1)
    if ($LASTEXITCODE -ne 0) { throw 'Python belum tersedia. Instal Python 3.11+ terlebih dahulu.' }
    $dependencyDir = Join-Path $env:TEMP 'NutriKos-python-deps'
    & uv pip install --python $pythonExe --target $dependencyDir -r (Join-Path $projectDir 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Pemasangan paket gagal. Periksa koneksi internet.' }
    $env:PYTHONPATH = $dependencyDir
    & $pythonExe -m streamlit run (Join-Path $projectDir 'app.py') --server.address localhost
} else {
    $pythonExe = Join-Path $projectDir '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonExe)) {
        & py -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Instal Python 3.11+ kemudian ulangi.' }
    }
    & $pythonExe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Pemasangan paket gagal.' }
    & $pythonExe -m streamlit run app.py --server.address localhost
}
