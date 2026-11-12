param(
    [Parameter(Mandatory=$true)][string]$ServerIP,
    [string]$PrivateDirectory = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) ('contrase' + [char]0x00F1 + 'as'))
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
Set-Location -LiteralPath $projectRoot
& $projectPython -B -m scripts.preparar_tls --server-ip $ServerIP --private-directory $PrivateDirectory
if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar TLS; revisa el diagnostico sin compartir claves.' }
