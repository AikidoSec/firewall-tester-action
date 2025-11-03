# Firewall Tester Action

This is an **internal validation framework** used to validate that firewall
agents work correctly.  
It runs QA tests against firewall agents in a Dockerized environment and checks
expected behaviors like startup events, heartbeats, runtime protection.

## 🚀 Usage

```yaml
jobs:
  run-firewall-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run Firewall QA Tests
        uses: AikidoSec/firewall-tester-action@v1
        with:
          dockerfile_path: ./test-app-dockerfiles/Dockerfile.hono
```

## 🧩 Inputs

| Name                  | Description                                                                                            |
| --------------------- | ------------------------------------------------------------------------------------------------------ |
| `dockerfile_path`     | Path to the Dockerfile with the Aikido agent installed (required)                                      |
| `extra_args`          | Extra arguments to pass to the `docker run` command (`--env`, `-e`, and `--env-file` only are allowed) |
| `extra_build_args`    | Extra arguments to pass to the `docker build` command (e.g. `--build-arg APP_VERSION=2.0.1`)           |
| `app_port`            | The port exposed by the application during Docker runtime                                              |
| `max_parallel_tests`  | Maximum number of tests to run in parallel (default: `5`)                                              |
| `config_update_delay` | Delay (in seconds) after updating the config to ensure it's applied (default: `60`)                    |
| `skip_tests`          | Comma-separated list of tests to skip (e.g. `test_allowed_ip,test_sql_injection`)                      |
| `test_timeout`        | Timeout (in seconds) for each test (default: `60`)                                                     |
| `sleep_before_test`   | Number of seconds to wait before starting the test (default: `1`)                                      |