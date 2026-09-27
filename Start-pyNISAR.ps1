# Run from this checkout. Prefer its own venv, with a local PyGeoObserver fallback.
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$taskPython = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    $taskPython = Join-Path $projectRoot '../foresteo/.venv/Scripts/python.exe'
}
if (-not (Test-Path -LiteralPath $taskPython)) {
    $taskPython = (Get-Command python).Source
}
$env:PYTHONPATH = Join-Path $projectRoot 'src'
# Avoid mixing a globally configured Conda PROJ database with a rasterio wheel.
$taskProj = & $taskPython -c "from pathlib import Path; import importlib.util; print(Path(importlib.util.find_spec('rasterio').origin).parent/'proj_data')"
if (Test-Path -LiteralPath $taskProj) {
    $env:PROJ_DATA = $taskProj
    $env:PROJ_LIB = $taskProj
}
Push-Location $projectRoot
try {
    & $taskPython -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8517 --server.headless true
} finally {
    Pop-Location
}
