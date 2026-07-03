param(
    [string] $DockerfilePath = $env:DOCKERFILE_PATH,
    [string] $BuildArgs = $env:BUILD_ARGS,
    [string] $AppPort = $env:APP_PORT,
    [string] $AppEnvFile = $env:APP_ENV_FILE,
    [string] $AppEnvFile2 = $env:APP_ENV_FILE_2,
    [string] $ConfigUpdateDelay = $env:CONFIG_UPDATE_DELAY,
    [string] $MaxParallelTests = $env:MAX_PARALLEL_TESTS,
    [string] $RunTests = $env:RUN_TESTS,
    [string] $SkipTests = $env:SKIP_TESTS,
    [string] $SleepBeforeTest = $env:SLEEP_BEFORE_TEST,
    [string] $TestName = $env:TEST_NAME,
    [string] $TestType = $env:TEST_TYPE,
    [string] $Command = 'run'
)

$ErrorActionPreference = 'Stop'

$bashCandidates = @(
    "$env:ProgramFiles\Git\bin\bash.exe",
    "$env:ProgramFiles\Git\usr\bin\bash.exe"
)

$bash = $null
foreach ($candidate in $bashCandidates) {
    if (Test-Path $candidate) {
        $bash = $candidate
        break
    }
}

if (-not $bash) {
    throw 'Could not find Git Bash. Install Git for Windows or set PATH to bash.exe.'
}

function Convert-ToBashPath {
    param([string] $Path)

    if (-not $Path) {
        return $Path
    }

    $resolved = Resolve-Path -LiteralPath $Path -ErrorAction Stop
    return $resolved.ProviderPath.Replace('\', '/')
}

if ($DockerfilePath) { $env:DOCKERFILE_PATH = Convert-ToBashPath $DockerfilePath }
if ($BuildArgs) { $env:BUILD_ARGS = $BuildArgs }
if ($AppPort) { $env:APP_PORT = $AppPort }
if ($AppEnvFile) { $env:APP_ENV_FILE = Convert-ToBashPath $AppEnvFile }
if ($AppEnvFile2) { $env:APP_ENV_FILE_2 = Convert-ToBashPath $AppEnvFile2 }
if ($ConfigUpdateDelay) { $env:CONFIG_UPDATE_DELAY = $ConfigUpdateDelay }
if ($MaxParallelTests) { $env:MAX_PARALLEL_TESTS = $MaxParallelTests }
if ($RunTests) { $env:RUN_TESTS = $RunTests }
if ($SkipTests) { $env:SKIP_TESTS = $SkipTests }
if ($SleepBeforeTest) { $env:SLEEP_BEFORE_TEST = $SleepBeforeTest }
if ($TestName) { $env:TEST_NAME = $TestName }
if ($TestType) { $env:TEST_TYPE = $TestType }

$script = Join-Path $PSScriptRoot 'run-compose-tests.sh'
& $bash $script $Command
exit $LASTEXITCODE
