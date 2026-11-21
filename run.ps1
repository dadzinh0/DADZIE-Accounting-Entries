$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker est introuvable. Installez Docker Desktop.' }
docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop ne répond pas. Démarrez Docker Desktop puis réessayez.' }
if (-not (Test-Path '.env')) {
    function New-Secret {
        $bytes = New-Object byte[] 48
        $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
        return ([BitConverter]::ToString($bytes) -replace '-', '').ToLowerInvariant()
    }
    @("POSTGRES_PASSWORD=$(New-Secret)", "SESSION_SECRET=$(New-Secret)") | Set-Content -Encoding ascii '.env'
    Write-Host 'Secrets locaux créés dans .env. Ne partagez pas ce fichier.'
}
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { throw 'Le démarrage Docker a échoué. Consultez les messages ci-dessus.' }
Write-Host 'Attente du service...'
for ($i = 0; $i -lt 60; $i++) {
    try { $response = Invoke-WebRequest -Uri 'http://localhost:8080/api/setup-status' -UseBasicParsing -TimeoutSec 2; if ($response.StatusCode -eq 200) { Write-Host 'Application disponible : http://localhost:8080'; Start-Process 'http://localhost:8080'; exit 0 } } catch { Start-Sleep -Seconds 2 }
}
throw 'Le service ne répond pas. Exécutez docker compose logs app pour diagnostiquer.'
