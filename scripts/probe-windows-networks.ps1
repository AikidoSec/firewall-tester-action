$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false

function Invoke-Docker([string[]]$Command) {
    & docker @Command
    if ($LASTEXITCODE -ne 0) {
        throw "docker $($Command -join ' ') exited with $LASTEXITCODE"
    }
}

function Show-Networks([string]$Stage) {
    Write-Host "::group::Networks: $Stage"
    $networkIds = @(Invoke-Docker @('network', 'ls', '-q'))
    if ($networkIds.Count -gt 0) {
        Invoke-Docker (@('network', 'inspect') + $networkIds)
    }
    Get-HnsNetwork | Select-Object Id, Name, Type, Subnets | ConvertTo-Json -Depth 6
    Write-Host '::endgroup::'
}

Start-Service docker -ErrorAction SilentlyContinue
for ($i = 0; $i -lt 60; $i++) {
    docker version
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 2
}
if ($LASTEXITCODE -ne 0) { throw 'Docker daemon did not become ready.' }

Show-Networks 'before setup'
$probeImage = $null
foreach ($image in @(Invoke-Docker @('image', 'ls', '--format', '{{.Repository}}:{{.Tag}}'))) {
    if ($image -like '*<none>*') { continue }
    if ((Invoke-Docker @('image', 'inspect', '--format', '{{.Os}}', $image)) -eq 'windows') {
        $probeImage = $image
        break
    }
}
if (-not $probeImage) {
    $probeImage = 'mcr.microsoft.com/windows/nanoserver:ltsc2022'
    Invoke-Docker @('pull', $probeImage)
}
Write-Host "Probe image: $probeImage"

$env:COMPOSE_PROJECT_NAME = 'firewall-tester-action'
$env:DEMO_CONTEXT = "$PWD/src/coremock"
$env:DEMO_DOCKERFILE = 'Dockerfile.windows'
$env:DEMO_IMAGE = 'unused-network-probe'
$env:APP_PORT = '80'
$env:RUNNER_TEMP_COMPOSE = $env:RUNNER_TEMP
$env:CONFIG_UPDATE_DELAY = '60'
$env:STARTUP_TIMEOUT = '600'
$config = (Invoke-Docker @('compose', '--profile', 'all', '--env-file', 'compose.windows.env', '-f', 'compose.yml', 'config', '--format', 'json')) -join "`n" | ConvertFrom-Json -AsHashtable
$probe = @{
    services = @{
        'network-probe' = @{
            image = $probeImage
            command = @('cmd', '/c', 'exit', '0')
            networks = @($config.networks.Keys)
        }
    }
    networks = $config.networks
}
$probeFile = Join-Path $env:RUNNER_TEMP 'qa-network-probe.json'
$probe | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $probeFile
$composeArgs = @('compose', '-p', 'firewall-tester-action', '-f', $probeFile)

try {
    for ($cycle = 1; $cycle -le 3; $cycle++) {
        Show-Networks "before cycle $cycle"
        Invoke-Docker ($composeArgs + @('down', '--timeout', '10', '--remove-orphans'))
        Invoke-Docker ($composeArgs + @('create', '--pull', 'never', '--no-build'))
        Show-Networks "created cycle $cycle"
        Invoke-Docker ($composeArgs + @('down', '--timeout', '10', '--remove-orphans'))
        Show-Networks "removed cycle $cycle"
    }
}
catch {
    Show-Networks 'failure before cleanup'
    throw
}
finally {
    Invoke-Docker ($composeArgs + @('down', '--timeout', '10', '--remove-orphans'))
}
