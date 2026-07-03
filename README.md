# Firewall Tester Action

Internal validation framework for Aikido firewall agents. Tests are orchestrated
with Docker Compose: each test directory has a `compose.yml` that starts the
mock core, Postgres, the demo app, and the Python test runner for that test.

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
          ref: dev-testing

      - uses: AikidoSec/firewall-tester-action@v1
        with:
          dockerfile_path: ./zen-demo/Dockerfile
          app_port: 3000
          skip_tests: test_stored_ssrf
```

Set `test_name` or `run_tests` to run a smaller subset. The CI workflow in this
repository runs all Linux demo apps through a GitHub matrix.

## Inputs

| Name                   | Description                                                       |
| ---------------------- | ----------------------------------------------------------------- |
| `dockerfile_path`      | Path to the Dockerfile with the Aikido agent installed            |
| `test_name`            | Optional single test directory under `server_tests`               |
| `run_tests`            | Optional comma-separated list of tests to run                     |
| `skip_tests`           | Optional comma-separated list of tests to skip                    |
| `app_port`             | Port exposed by the application during Docker runtime             |
| `config_update_delay`  | Delay in seconds after runtime config updates                     |
| `app_env_file`         | Optional env file passed to the application service               |
| `app_env_file_2`       | Optional second env file passed to the application service        |
| `max_parallel_tests`   | Maximum number of Compose tests to run in parallel                |

## Running Locally

Clone a demo app into `./zen-demo`:

```sh
git clone git@github.com:Aikido-demo-apps/zen-demo-nodejs.git zen-demo
```

Run a single test directly with Docker Compose:

```sh
COMPOSE_PROJECT_NAME=test_sql_injection DEMO_CONTEXT=./zen-demo \
  DEMO_IMAGE=firewall-tester-action-demo-nodejs APP_PORT=3000 \
  docker compose --env-file compose.linux.env -f compose.yml \
  up --build --exit-code-from test_sql_injection test_sql_injection
```

Clean up after a run:

```sh
COMPOSE_PROJECT_NAME=test_sql_injection DEMO_CONTEXT=./zen-demo \
  DEMO_IMAGE=firewall-tester-action-demo-nodejs APP_PORT=3000 \
  docker compose --env-file compose.linux.env -f compose.yml \
  down -v --remove-orphans
```
