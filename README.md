# Firewall Tester Action

Internal validation framework for Aikido firewall agents. Tests are orchestrated
with Docker Compose: each test directory has a `compose.yml` that starts the
mock core, Postgres, the demo app, and the Python test runner for that test.

## Usage

Run one test with the composite action:

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
          ref: dev-testing

      - uses: AikidoSec/firewall-tester-action@v1
        with:
          dockerfile_path: ./zen-demo/Dockerfile
          test_name: test_sql_injection
          app_port: 3000
```

The CI workflow in this repository runs all Linux demo apps through a GitHub
matrix, with one Compose test per matrix job.

## Inputs

| Name                   | Description                                                       |
| ---------------------- | ----------------------------------------------------------------- |
| `dockerfile_path`      | Path to the Dockerfile with the Aikido agent installed            |
| `test_name`            | Test directory under `server_tests`, such as `test_sql_injection` |
| `app_port`             | Port exposed by the application during Docker runtime             |
| `config_update_delay`  | Delay in seconds after runtime config updates                     |
| `sleep_before_test`    | Seconds to wait before starting the test                          |
| `app_env_file`         | Optional env file passed to the application service               |
| `app_env_file_2`       | Optional second env file passed to the application service        |
| `php_firewall_version` | Optional PHP firewall package version build arg                   |

## Running Locally

Clone a demo app into `./zen-demo`:

```sh
git clone git@github.com:Aikido-demo-apps/zen-demo-nodejs.git zen-demo
```

Run a single test directly with Docker Compose:

```sh
COMPOSE_PROJECT_NAME=test_sql_injection DEMO_CONTEXT=./zen-demo APP_PORT=3000 SLEEP_BEFORE_TEST=15 \
  docker compose -f compose.linux.yml -f server_tests/test_sql_injection/compose.yml \
  up --build --exit-code-from test test
```

Clean up after a run:

```sh
COMPOSE_PROJECT_NAME=test_sql_injection DEMO_CONTEXT=./zen-demo APP_PORT=3000 \
  docker compose -f compose.linux.yml -f server_tests/test_sql_injection/compose.yml \
  down -v --remove-orphans
```
