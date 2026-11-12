param([switch]$Remove)
$ErrorActionPreference = 'Stop'
$ruleName = 'ReportesPro-Pruebas-TLS-8502'
if ($Remove) {
    Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    Write-Output 'Regla de pruebas retirada si existia.'
    exit 0
}
$projectRoot = Split-Path -Parent $PSScriptRoot
$projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) { throw 'Falta el Python del proyecto.' }
if (-not (Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name $ruleName -DisplayName 'ReportesPro prueba HTTPS LAN' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8502 -Program $projectPython -Profile Private -RemoteAddress LocalSubnet | Out-Null
}
Write-Output 'Regla limitada a red Privada, subred local y TCP 8502. No abre administracion ni Internet.'
