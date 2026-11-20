$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$localDirectory = Join-Path $projectRoot '.local'
New-Item -ItemType Directory -Path $localDirectory -Force | Out-Null
$destination = Join-Path $localDirectory 'cloudflared.exe'
if (Test-Path -LiteralPath $destination) {
    Write-Host 'El conector ya existe. No se sobrescribio.'
    exit 0
}
$temporaryFile = Join-Path $localDirectory ([guid]::NewGuid().ToString('N') + '.download')
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $release = Invoke-RestMethod -Uri 'https://api.github.com/repos/cloudflare/cloudflared/releases/latest' -TimeoutSec 30
    $asset = @($release.assets | Where-Object { $_.name -eq 'cloudflared-windows-amd64.exe' })
    if ($asset.Count -ne 1 -or $asset[0].digest -notmatch '^sha256:[a-fA-F0-9]{64}$') {
        throw 'La fuente oficial no devolvio una huella SHA256 valida. No se instalara el archivo.'
    }
    $downloadUrl = [string]$asset[0].browser_download_url
    if (-not $downloadUrl.StartsWith('https://github.com/cloudflare/cloudflared/releases/download/')) {
        throw 'Origen de descarga inesperado. No se instalara el archivo.'
    }
    Write-Host 'Descargando el conector oficial de Cloudflare...'
    Invoke-WebRequest -Uri $downloadUrl -OutFile $temporaryFile -UseBasicParsing -TimeoutSec 180
    $expectedHash = $asset[0].digest.Substring(7)
    if ((Get-FileHash -LiteralPath $temporaryFile -Algorithm SHA256).Hash -ne $expectedHash) {
        throw 'La huella del archivo no coincide. No se instalara el conector.'
    }
    Move-Item -LiteralPath $temporaryFile -Destination $destination
    Write-Host 'Conector instalado y SHA256 verificado. Ahora abre 3 - Iniciar HTTPS temporal.'
} finally {
    if (Test-Path -LiteralPath $temporaryFile) { Remove-Item -LiteralPath $temporaryFile }
}
