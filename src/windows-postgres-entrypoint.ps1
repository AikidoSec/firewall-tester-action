$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

Write-Host "Ensuring PGDATA directory permissions..."
New-Item -Path "$env:PGDATA" -ItemType Directory -Force | Out-Null
& icacls "$env:PGDATA" /grant "${env:USERNAME}:(OI)(CI)F" | Out-Null

$env:PATH += ";$env:PGBINS"

if (-not $env:POSTGRES_USER) {
    $env:POSTGRES_USER = "postgres"
}

if (-not $env:POSTGRES_DB) {
    $env:POSTGRES_DB = $env:POSTGRES_USER
}

$pgCtlArgs = "-c listen_addresses=* -c max_connections=200"
$needsInit = -not (Test-Path -Path "$env:PGDATA\PG_VERSION")

if ($needsInit) {
    $initdbArgs = @("-U", "$env:POSTGRES_USER", "-E", "UTF8", "--no-locale")

    if ($env:POSTGRES_PASSWORD) {
        $pwFile = New-TemporaryFile
        $env:POSTGRES_PASSWORD | Out-File -FilePath "$pwFile" -Force -Encoding utf8
        $initdbArgs += "--pwfile", "$pwFile"
    }

    if ($env:POSTGRES_INITDB_WALDIR) {
        $initdbArgs += "--waldir", "$env:POSTGRES_INITDB_WALDIR"
    }

    if ($env:POSTGRES_INITDB_ARGS) {
        $initdbArgs += $env:POSTGRES_INITDB_ARGS.Split(' ')
    }

    Write-Host "Initializing database..."
    & initdb @initdbArgs "$env:PGDATA" | Out-Default

    if ($pwFile) {
        Remove-Item -Path "$pwFile" -Force
    }

    $authMethod = if ($env:POSTGRES_PASSWORD) { "scram-sha-256" } else { "trust" }
    $hostRule = "host all all all $authMethod"
    Add-Content -Path "$env:PGDATA\pg_hba.conf" -Value $hostRule

    & pg_ctl -U "$env:POSTGRES_USER" -D "$env:PGDATA" -o $pgCtlArgs -w start | Out-Default

    try {
        if ($env:POSTGRES_DB -ne "postgres") {
            & psql -v ON_ERROR_STOP=1 --username "$env:POSTGRES_USER" --dbname "postgres" -c "CREATE DATABASE `"$($env:POSTGRES_DB)`";" | Out-Default
        }
    }
    finally {
        & pg_ctl -U "$env:POSTGRES_USER" -D "$env:PGDATA" -m fast -w stop | Out-Default
    }
}

Write-Host "Registering PostgreSQL service..."
if (-not (Get-Service -Name "postgresql" -ErrorAction SilentlyContinue)) {
    & pg_ctl register -D "$env:PGDATA" -N postgresql -o $pgCtlArgs | Out-Default
}

Write-Host "Starting PostgreSQL service..."
Start-Service -Name postgresql

while ((Get-Service -Name postgresql).Status -ne "Running") {
    Start-Sleep -Seconds 1
}

Write-Host "Waiting on PostgreSQL service..."
Wait-Process -Name postgres
