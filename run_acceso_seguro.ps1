param(
    [string]$CloudflaredPath = (Join-Path $PSScriptRoot '.local\cloudflared.exe')
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $CloudflaredPath -PathType Leaf)) {
    throw 'Falta cloudflared.exe. Consulta docs\ACCESO_SEGURO_MOVIL.md. No se publico la aplicacion.'
}
# Un puerto exclusivo evita exponer por accidente la instancia administrativa.
$probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 8503)
try { $probe.Start() } finally { $probe.Stop() }
& $projectPython -B -m scripts.diagnostico --security-config
if ($LASTEXITCODE -ne 0) { throw 'El diagnostico requiere revision.' }

$runDirectory = Join-Path $PSScriptRoot ('.local\acceso_seguro_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $runDirectory | Out-Null
$outputLog = Join-Path $runDirectory 'tunnel-out.log'
$errorLog = Join-Path $runDirectory 'tunnel-error.log'
$previousMode = $env:REPORTESPRO_ACCESS_MODE
$previousPublicUrl = $env:REPORTESPRO_PUBLIC_URL
$tunnel = $null
$resultCode = 1
try {
    Write-Host 'Creando enlace HTTPS temporal para pruebas. Ctrl+C lo cierra.'
    $tunnel = Start-Process -FilePath $CloudflaredPath -ArgumentList @(
        'tunnel', '--no-autoupdate', '--url', 'http://127.0.0.1:8503'
    ) -PassThru -WindowStyle Hidden -RedirectStandardOutput $outputLog -RedirectStandardError $errorLog
    $publicUrl = $null
    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline) {
        $tunnel.Refresh()
        if ($tunnel.HasExited) { throw 'Cloudflare no pudo iniciar. Consulta los logs en .local sin compartir datos privados.' }
        $logText = ((Get-Content -LiteralPath $outputLog,$errorLog -Raw -ErrorAction SilentlyContinue) -join "`n")
        $urlMatch = [regex]::Match($logText, 'https://[a-z0-9-]+\.trycloudflare\.com')
        if ($urlMatch.Success) { $publicUrl = $urlMatch.Value + '/'; break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $publicUrl) { throw 'No se obtuvo un enlace HTTPS en 60 segundos. Revisa la conexion a Internet.' }
    $env:REPORTESPRO_ACCESS_MODE = 'lan'
    $env:REPORTESPRO_PUBLIC_URL = $publicUrl
    $linkPath = Join-Path $PSScriptRoot 'Accesos ReportesPro\3 - Abrir enlace seguro temporal.url'
    Set-Content -LiteralPath $linkPath -Value "[InternetShortcut]`r`nURL=$publicUrl" -Encoding ASCII
    Write-Host "ENLACE PARA PC Y CELULARES: $publicUrl"
    Write-Host 'Deja esta ventana abierta. Usa cuentas de usuario; el administrador sigue solo en localhost:8501.'
    Write-Host 'Es un enlace de pruebas por Internet: usa archivos sinteticos. Al cerrar, el enlace caduca.'
    & $projectPython -m streamlit run web_app.py --server.address 127.0.0.1 --server.port 8503 --server.maxUploadSize 10 --server.enableCORS true --server.enableXsrfProtection true --browser.serverAddress ([uri]$publicUrl).Host --browser.serverPort 443
    $resultCode = $LASTEXITCODE
} finally {
    $env:REPORTESPRO_ACCESS_MODE = $previousMode
    $env:REPORTESPRO_PUBLIC_URL = $previousPublicUrl
    if ($null -ne $tunnel) {
        $tunnel.Refresh()
        if (-not $tunnel.HasExited) { Stop-Process -Id $tunnel.Id -ErrorAction SilentlyContinue }
    }
}
exit $resultCode
