$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Falta el entorno .venv. Consulta docs/OPERACION.md.'
}
& $projectPython -B -m scripts.diagnostico --security-config
if ($LASTEXITCODE -ne 0) {
    throw 'La comprobacion previa requiere revision. No se inicio el servidor.'
}
$previousMode = $env:REPORTESPRO_ACCESS_MODE
try {
    $env:REPORTESPRO_ACCESS_MODE = 'local'
    & $projectPython -m streamlit run web_app.py --server.address 127.0.0.1 --server.port 8501 --server.maxUploadSize 10
    $resultCode = $LASTEXITCODE
} finally {
    $env:REPORTESPRO_ACCESS_MODE = $previousMode
}
exit $resultCode
