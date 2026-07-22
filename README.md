# Firewall Tester Action

Internal validation framework for Aikido firewall agents. Tests are orchestrated
with Docker Compose: a shared mock core, PostgreSQL database, and suite runner
coordinate an isolated demo-app service for every selected test.

## Usage

Run the full server test suite with the composite action:

```yaml
jobs:
  run-firewall-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/checkout@v4
        with:
          repository: Aikido-demo-apps/zen-demo-nodejs
          path: ./zen-demo
          ref: main

      - uses: AikidoSec/firewall-tester-action@v1
        with:
          dockerfile_path: ./zen-demo/Dockerfile
          app_port: 3000
          build_args: |
            AGENT_VERSION=1.2.3
          skip_tests: test-stored-ssrf
```

Set `test_name` or `run_tests` to run a smaller subset. The CI workflow in this
repository runs all Linux demo apps through a GitHub matrix.

## Inputs

| Name                  | Description                                                     |
| --------------------- | --------------------------------------------------------------- |
| `dockerfile_path`     | Path to the Dockerfile with the Aikido agent installed          |
| `test_name`           | Optional single test directory under `server_tests`             |
| `run_tests`           | Optional comma-separated list of tests to run                   |
| `skip_tests`          | Optional comma-separated list of tests to skip                  |
| `build_args`          | Optional newline-separated Docker build args for the demo image |
| `app_port`            | Port exposed by the application during Docker runtime           |
| `max_parallel_tests`  | Maximum concurrent Compose operations and tests (default: 20)   |
| `config_update_delay` | Delay after runtime configuration updates (default: 60 seconds) |
| `app_env_file`        | Optional env file passed to the application service             |
| `app_env_file_2`      | Optional second env file passed to the application service      |

## Running Locally

Clone a demo app into `./zen-demo`:

```sh
git clone git@github.com:Aikido-demo-apps/zen-demo-nodejs.git zen-demo
```

Run the same Compose path used by the action:

```powershell
.\scripts\run-compose-tests.ps1 `
  -DockerfilePath .\zen-demo\Dockerfile `
  -AppPort 3000 `
  -TestName test-sql-injection
```

The PowerShell wrapper calls Git Bash. You can also call the bash script
directly:

```sh
DOCKERFILE_PATH=./zen-demo/Dockerfile \
APP_PORT=3000 \
TEST_NAME=test-sql-injection \
bash ./scripts/run-compose-tests.sh
```
