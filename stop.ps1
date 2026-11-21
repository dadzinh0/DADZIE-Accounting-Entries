$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
docker compose stop
if ($LASTEXITCODE -ne 0) { throw 'Arrêt impossible. Vérifiez Docker Desktop.' }
Write-Host 'Services arrêtés. Les volumes et données restent conservés.'
