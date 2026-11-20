param([switch]$DesdeEscritorio)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Falta el entorno .venv. Consulta docs/OPERACION.md.'
}
if ($DesdeEscritorio) {
    $wifi = [System.Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces() |
        Where-Object { $_.OperationalStatus -eq 'Up' -and $_.NetworkInterfaceType -eq 'Wireless80211' }
    $direccion = $wifi | ForEach-Object { $_.GetIPProperties().UnicastAddresses } |
        Where-Object { $_.Address.AddressFamily -eq 'InterNetwork' -and $_.Address.IPAddressToString -notlike '169.254.*' } |
        Select-Object -First 1 -ExpandProperty Address
    if ($direccion) {
        $urlAvances = "http://${direccion}:8504/avances"
        try {
            $null = Invoke-WebRequest -Uri $urlAvances -Method Head -UseBasicParsing -TimeoutSec 1
        } catch {
            $argumentos = @('-B', '-m', 'scripts.servir_avances', '--direccion', $direccion.IPAddressToString)
            Start-Process -FilePath $projectPython -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -ArgumentList $argumentos
        }
        Write-Host "Avances desde el Wi-Fi: $urlAvances"
    }

    try {
        $servidorLocal = Invoke-WebRequest -Uri 'http://127.0.0.1:8501/_stcore/health' -UseBasicParsing -TimeoutSec 1
    } catch {
        $servidorLocal = $null
    }
    if ($servidorLocal -and $servidorLocal.Content -eq 'ok') {
        Start-Process 'http://127.0.0.1:8501/'
        return
    }
}

& $projectPython -B -m scripts.diagnostico --security-config
if ($LASTEXITCODE -ne 0) {
    throw 'La comprobacion previa requiere revision. No se inicio el servidor.'
}
$previousMode = $env:REPORTESPRO_ACCESS_MODE
try {
    $env:REPORTESPRO_ACCESS_MODE = 'local'
    $opciones = @()
    if ($DesdeEscritorio) {
        $opciones = @('--server.headless=false', '--server.runOnSave=true')
    }
    & $projectPython -m streamlit run web_app.py --server.address 127.0.0.1 --server.port 8501 --server.maxUploadSize 10 @opciones
    $resultCode = $LASTEXITCODE
} finally {
    $env:REPORTESPRO_ACCESS_MODE = $previousMode
}
exit $resultCode
