# Compose-Native Individual Test Migration

## Summary

Migrate all tests away from `run_test.py` orchestration using per-test Compose
files that reference shared platform base files. Do not add named suites yet,
and do not implement the GitHub matrix yet. Local usage starts one explicit test
directly with Docker Compose.

## Key Changes

- Use root `compose.yml` with `compose.linux.env` or `compose.windows.env` for
  shared platform infrastructure.
- Each test directory has its own `compose.yml`; `TEST_NAME` and `TEST_TOKEN`
  are derived from Compose's project name.
- Each test is runnable directly, naming only the test service:
  - `DEMO_CONTEXT=../zen-demo-nodejs DEMO_IMAGE=firewall-tester-action-demo-nodejs APP_PORT=3000 docker compose --env-file compose.linux.env -f compose.yml up --build --exit-code-from test_sql_injection test_sql_injection`
- Windows container mode selects the Windows env file:
  - `DEMO_CONTEXT=../zen-demo-dotnet-framework DEMO_IMAGE=firewall-tester-action-demo-dotnet-framework APP_PORT=80 docker compose --env-file compose.windows.env -f compose.yml up --build --exit-code-from test_sql_injection test_sql_injection`
- Do not add `suite_all`, `suite_server`, or other suite aggregator services
  yet.
- Do not add GitHub Actions matrix changes yet.
- Remove `run_test.py` only after every test can be run directly through
  Compose.

## Implementation Changes

- Core mock:
  - Add `/health` for Compose healthchecks.
  - Allow deterministic token creation through `/api/runtime/apps`.
- Test runner:
  - Keep `testlib.py` as helper code.
  - Add environment-based host overrides: `TEST_SERVER_HOST`, `TEST_CORE_HOST`,
    and `TEST_CONTROL_SERVER_HOST`, defaulting to `localhost`.
  - Remove Docker CLI orchestration from test files.
- Compose model:
  - Platform bases define only shared `core`, `postgres`, setup, app, and runner
    services.
  - Per-test Compose files include the selected platform base.
  - Common tests only declare the platform include.
  - Special tests declare their own extra sidecars, networks, volumes, logging,
    or env overrides.
  - Test services reach app/core over Compose DNS; app-to-core keeps the
    existing static core IP so outbound-domain tests preserve their allowlist
    assumptions.
  - No host-published app ports are needed.
  - Per-test setup applies `start_config.json` and `start_firewall.json` when
    present.
- Special cases:
  - `test_invalid_token` keeps its invalid `AIKIDO_TOKEN`.
  - `test_no_token_set` receives no default `AIKIDO_TOKEN`.
  - `test_internet_not_available` keeps intentionally unreachable core endpoint
    envs.
  - Control tests pass `--control_server_port 8081` and use the app service as
    both server/control host as needed.
  - SSRF tests use Compose sidecars; stored SSRF uses DNS mocking instead of
    `/etc/hosts`.
  - `test_logs_sensitive_data` reads app logs from a shared volume, not
    `docker logs`.

## Test Plan

- Static checks:
  - `docker compose config`
  - `python -m py_compile server_tests/**/*.py`
  - `npm run lint -- --quiet`
  - Prettier check for changed Compose/TS files
- Runtime checks:
  - Run one basic test service.
  - Run one special env test.
  - Run one control test.
  - Run outbound-domain with DNS/network alias behavior.
  - Run SSRF/stored-SSRF on Linux and Windows Docker environments.

## Assumptions

- First Compose version optimizes for direct individual test execution, not
  all-tests aggregation.
- Parallelization and GitHub matrix orchestration will be designed later.
- No Python/Node wrapper should replace `run_test.py`; Compose remains the
  orchestration interface.
