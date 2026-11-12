param([string]$ServerIP)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$networkConfig = Join-Path $PSScriptRoot '.local\red.json'
if (-not (Test-Path -LiteralPath $networkConfig)) {
    throw 'Falta TLS. Ejecuta scripts\configurar_tls_red.ps1 -ServerIP TU_IP_PRIVADA.'
}
$settings = Get-Content -LiteralPath $networkConfig -Raw | ConvertFrom-Json
if (-not $ServerIP) { $ServerIP = $settings.server_ip }
if ($ServerIP -ne $settings.server_ip) {
    throw 'La IP difiere del certificado. Regenera TLS con configurar_tls_red.ps1.'
}
if (-not (Test-Path -LiteralPath $settings.certificate) -or -not (Test-Path -LiteralPath $settings.private_key)) {
    throw 'Faltan el certificado o la clave de TLS. No se inicio la red.'
}
& $projectPython -B -m scripts.diagnostico --security-config
if ($LASTEXITCODE -ne 0) { throw 'El diagnostico requiere revision.' }
$previousMode = $env:REPORTESPRO_ACCESS_MODE
$previousPublicUrl = $env:REPORTESPRO_PUBLIC_URL
try {
    $env:REPORTESPRO_ACCESS_MODE = 'lan'
    $env:REPORTESPRO_PUBLIC_URL = "https://$($ServerIP):8502/"
    & $projectPython -m streamlit run web_app.py --server.address $ServerIP --server.port 8502 --server.maxUploadSize 10 --server.sslCertFile $settings.certificate --server.sslKeyFile $settings.private_key
    $resultCode = $LASTEXITCODE
} finally {
    $env:REPORTESPRO_ACCESS_MODE = $previousMode
    $env:REPORTESPRO_PUBLIC_URL = $previousPublicUrl
}
exit $resultCode
