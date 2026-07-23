import concurrent.futures
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

import psycopg
from psycopg import sql
import requests

from core_api import CoreApi


IS_WINDOWS = os.name == "nt"
WORKSPACE = Path(os.environ.get("WORKSPACE_ROOT", r"C:\workspace" if IS_WINDOWS else "/workspace"))
SERVER_TESTS = WORKSPACE / "server_tests"
RESULTS = Path(os.environ.get("SUITE_RESULTS_DIR", r"C:\results" if IS_WINDOWS else "/results"))
SETUP_COMPLETE = RESULTS / "setup-complete"
SUITE_COMPLETE = RESULTS / "suite-complete"
TESTS_WITHOUT_STARTUP_CONFIG = {
    "test-aikido-disable",
    "test-internet-not-available",
    "test-invalid-token",
    "test-no-token-set",
}
TEST_NAME_PATTERN = re.compile(r"^(?:test|control-test)-[a-z0-9][a-z0-9-]*$")


def csv_values(name: str) -> list[str]:
    return [value.strip() for value in os.environ.get(name, "").split(",") if value.strip()]


def token_for(test_name: str) -> str:
    return f"AIK_RUNTIME_1_{test_name}"


def control_server_port() -> str:
    return os.environ.get("CONTROL_SERVER_PORT") or "8081"


def connect_to_database() -> psycopg.Connection:
    return psycopg.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ["POSTGRES_ADMIN_USER"],
        password=os.environ["POSTGRES_ADMIN_PASSWORD"],
        dbname="postgres",
        autocommit=True,
    )


def prepare_database_role(connection: psycopg.Connection) -> None:
    database_user = os.environ["POSTGRES_USER"]
    database_password = os.environ["POSTGRES_PASSWORD"]

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (database_user,))
        role_exists = cursor.fetchone() is not None
        role_statement = sql.SQL(
            "ALTER ROLE {} WITH LOGIN PASSWORD {}"
            if role_exists
            else "CREATE ROLE {} WITH LOGIN PASSWORD {}"
        ).format(sql.Identifier(database_user), sql.Literal(database_password))
        cursor.execute(role_statement)


def prepare_database(connection: psycopg.Connection, test_name: str) -> None:
    database_user = os.environ["POSTGRES_USER"]
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (test_name,))
        if cursor.fetchone() is None:
            cursor.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(test_name), sql.Identifier(database_user)
                )
            )


def request_core(method: str, path: str, **kwargs) -> requests.Response:
    deadline = time.monotonic() + 60
    last_error = None

    with requests.Session() as session:
        session.trust_env = False
        for attempt in range(10):
            try:
                remaining_seconds = deadline - time.monotonic()
                if remaining_seconds <= 0:
                    break
                response = session.request(
                    method,
                    f"{os.environ['CORE_URL']}{path}",
                    timeout=min(10, remaining_seconds),
                    **kwargs,
                )
                response.raise_for_status()
                return response
            except requests.RequestException as error:
                last_error = error
                if attempt < 9:
                    time.sleep(min(2, max(0, deadline - time.monotonic())))

    raise RuntimeError(f"Core setup request failed: {last_error}")


def run_setup(test_name: str, database: psycopg.Connection) -> None:
    if not TEST_NAME_PATTERN.fullmatch(test_name):
        raise RuntimeError(f"Invalid test name: {test_name}")
    test_dir = SERVER_TESTS / test_name
    if not (test_dir / "test.py").is_file():
        raise RuntimeError(f"Unknown test: {test_name}")

    print(f"SETUP {test_name}", flush=True)
    print(f"Preparing database for {test_name}", flush=True)
    prepare_database(database, test_name)

    token = token_for(test_name)
    headers = {"Authorization": token}
    print("Registering core app token", flush=True)
    request_core("POST", "/api/runtime/apps", json={"token": token})

    config_path = test_dir / "start_config.json"
    if config_path.is_file():
        print("Uploading runtime config", flush=True)
        request_core(
            "POST",
            "/api/runtime/config",
            headers=headers,
            json=json.loads(config_path.read_text(encoding="utf-8")),
        )

    firewall_path = test_dir / "start_firewall.json"
    if firewall_path.is_file():
        print("Uploading firewall lists", flush=True)
        request_core(
            "POST",
            "/api/runtime/firewall/lists",
            headers=headers,
            json=json.loads(firewall_path.read_text(encoding="utf-8")),
        )

    print("Validating core app token", flush=True)
    request_core("GET", "/api/runtime/events", headers=headers)
    print(f"Setup completed for {test_name}", flush=True)


def wait_for_app(test_name: str, app_host: str, output, deadline: float) -> None:
    is_control_test = test_name.startswith("control-test-")
    port = int(
        control_server_port()
        if is_control_test
        else os.environ.get("APP_PORT", "8080")
    )
    last_error = None

    while time.monotonic() < deadline:
        try:
            with socket.create_connection((app_host, port), timeout=2):
                break
        except OSError as error:
            last_error = error
            print(
                f"Waiting for {'control server' if is_control_test else 'app'} "
                f"TCP port at {app_host}:{port}: {error}",
                file=output,
                flush=True,
            )
            time.sleep(2)
    else:
        raise RuntimeError(
            f"{'Control server' if is_control_test else 'App'} TCP port did not "
            f"become reachable at "
            f"{app_host}:{port}: {last_error}"
        )

    if is_control_test:
        return

    # Give every agent the same one-request baseline and start agents whose
    # application initializes only while handling its first request.
    initial_url = f"http://{app_host}:{port}/"
    with requests.Session() as session:
        session.trust_env = False
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            raise RuntimeError("Startup deadline expired before the initial request")
        response = session.get(
            initial_url,
            timeout=remaining_seconds,
            allow_redirects=False,
        )
        print(
            f"Initial request completed with HTTP {response.status_code}",
            file=output,
            flush=True,
        )


def wait_for_startup_config(test_name: str, output, deadline: float) -> None:
    if test_name in TESTS_WITHOUT_STARTUP_CONFIG:
        return

    core_host = os.environ.get("CORE_HOST", "core")
    remaining_seconds = deadline - time.monotonic()
    if remaining_seconds <= 0:
        raise RuntimeError("Startup deadline expired before config delivery")

    core = CoreApi(
        token=token_for(test_name),
        core_url=f"http://{core_host}:3000",
        test_name=test_name,
    )
    core.wait_for_config_delivery(timeout_seconds=remaining_seconds)
    print(
        "Agent fetched its startup configuration and firewall lists",
        file=output,
        flush=True,
    )


def test_environment(test_name: str) -> dict[str, str]:
    environment = os.environ.copy()
    app_host = test_name
    environment.update(
        {
            "PYTHONPATH": str(SERVER_TESTS),
            "PYTHONUNBUFFERED": "1",
            "TEST_SERVER_HOST": app_host,
            "TEST_CONTROL_SERVER_HOST": app_host,
            "TEST_CORE_HOST": os.environ.get("CORE_HOST", "core"),
            "TEST_DNS_MOCK_URL": "",
            "TEST_APP_LOG_FILE": "",
        }
    )
    if test_name in {"test-stored-ssrf", "test-stored-ssrf-no-context"}:
        environment["TEST_DNS_MOCK_URL"] = f"http://dns-mock-{test_name}:8053"
    if test_name == "test-logs-sensitive-data":
        environment["TEST_APP_LOG_FILE"] = str(
            Path(os.environ["TEST_LOG_DIR"]) / "test-logs-sensitive-data.log"
        )
    return environment


def run_test(test_name: str) -> dict:
    started = time.monotonic()
    log_path = RESULTS / f"{test_name}.log"
    app_host = test_name
    app_port = os.environ.get("APP_PORT", "8080")
    startup_timeout = int(os.environ.get("STARTUP_TIMEOUT", "600"))
    startup_deadline = time.monotonic() + startup_timeout

    with log_path.open("w", encoding="utf-8", errors="replace") as output:
        try:
            wait_for_app(test_name, app_host, output, startup_deadline)
            if not test_name.startswith("control-test-"):
                wait_for_startup_config(test_name, output, startup_deadline)

            command = [
                sys.executable,
                str(SERVER_TESTS / test_name / "test.py"),
                "--test_name",
                test_name,
                "--server_port",
                app_port,
                "--token",
                token_for(test_name),
            ]
            if test_name.startswith("control-test-"):
                command.extend(
                    ["--control_server_port", control_server_port()]
                )

            result = subprocess.run(
                command,
                cwd=SERVER_TESTS,
                env=test_environment(test_name),
                stdout=output,
                stderr=subprocess.STDOUT,
                check=False,
            )
            exit_code = result.returncode
            error = "" if exit_code == 0 else f"Exit code {exit_code}"
        except Exception as exception:
            print(f"Runner error: {exception}", file=output, flush=True)
            exit_code = 1
            error = str(exception)

    result = {
        "test": test_name,
        "status": "PASS" if exit_code == 0 else "FAIL",
        "duration_seconds": round(time.monotonic() - started, 2),
        "error": error,
        "log": str(log_path),
    }
    return result


def tail(path: Path, line_count: int = 200) -> str:
    try:
        return "".join(
            path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)[-line_count:]
        )
    except OSError as error:
        return f"Could not read {path}: {error}\n"


def write_summary(results: list[dict], skipped: list[str]) -> None:
    ordered = sorted(results, key=lambda result: result["test"])
    passed = sum(result["status"] == "PASS" for result in ordered)
    failed = sum(result["status"] == "FAIL" for result in ordered)
    total = len(ordered) + len(skipped)

    print("\nTest Results Summary", flush=True)
    print("====================", flush=True)
    print(f"Total Tests: {total}", flush=True)
    print(f"Passed: {passed}", flush=True)
    print(f"Skipped: {len(skipped)}", flush=True)
    print(f"Failed: {failed}", flush=True)
    print("\nDetailed Results:", flush=True)
    for result in ordered:
        print(
            f"{result['test']:<55} {result['status']:<5} "
            f"{result['duration_seconds']:>8.2f}s {result['error']}",
            flush=True,
        )
    for test_name in sorted(skipped):
        print(f"{test_name:<55} SKIP       N/A Skipped", flush=True)

    summary = {
        "total": total,
        "passed": passed,
        "skipped": len(skipped),
        "failed": failed,
        "results": ordered,
        "skipped_tests": sorted(skipped),
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    markdown = [
        "## Test Results Summary",
        "",
        f"- **Total Tests:** {total}",
        f"- **Passed:** {passed}",
        f"- **Skipped:** {len(skipped)}",
        f"- **Failed:** {failed}",
        "",
        "| Test | Status | Duration | Error |",
        "|------|--------|----------|-------|",
    ]
    for result in ordered:
        error = result["error"].replace("|", "\\|").replace("\n", "<br>")
        markdown.append(
            f"| {result['test']} | {result['status']} | "
            f"{result['duration_seconds']:.2f}s | {error} |"
        )
    for test_name in sorted(skipped):
        markdown.append(f"| {test_name} | SKIP | N/A | Skipped |")
    markdown.append("")
    (RESULTS / "summary.md").write_text("\n".join(markdown), encoding="utf-8")

    failures = "\n".join(result["test"] for result in ordered if result["status"] == "FAIL")
    (RESULTS / "failures.txt").write_text(
        failures + ("\n" if failures else ""), encoding="utf-8"
    )


def main() -> int:
    tests = csv_values("SUITE_TESTS")
    skipped = csv_values("SUITE_SKIPPED_TESTS")

    RESULTS.mkdir(parents=True, exist_ok=True)
    SETUP_COMPLETE.unlink(missing_ok=True)
    SUITE_COMPLETE.unlink(missing_ok=True)

    setup_started = time.monotonic()
    test_name = tests[0] if tests else "suite-setup"
    try:
        if tests:
            with connect_to_database() as database:
                prepare_database_role(database)
                for test_name in tests:
                    run_setup(test_name, database)
    except Exception as exception:
        setup_seconds = round(time.monotonic() - setup_started, 2)
        result = {
            "test": test_name,
            "status": "FAIL",
            "duration_seconds": setup_seconds,
            "error": str(exception),
            "log": "",
        }
        write_summary([result], skipped)
        print(f"SETUP FAILED: {exception}", flush=True)
        return 1

    setup_seconds = round(time.monotonic() - setup_started, 2)
    print(f"SETUP COMPLETE ({setup_seconds:.2f}s)", flush=True)
    SETUP_COMPLETE.touch()

    results = []
    if tests:
        print(f"RUNTIME SERVICES READY ({len(tests)} tests)", flush=True)

        configured_workers = os.environ.get("SUITE_MAX_WORKERS")
        max_workers = min(
            len(tests), int(configured_workers) if configured_workers else len(tests)
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(run_test, test_name): test_name
                for test_name in tests
            }
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
                print(
                    f"{result['status']} {result['test']} "
                    f"({result['duration_seconds']:.2f}s)",
                    flush=True,
                )
                if result["status"] == "FAIL":
                    print(f"--- {result['test']} log ---", flush=True)
                    print(tail(Path(result["log"])), end="", flush=True)
                    print(f"--- end {result['test']} log ---", flush=True)

    write_summary(results, skipped)
    SUITE_COMPLETE.touch()
    return 1 if any(result["status"] == "FAIL" for result in results) else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exception:
        print(f"Suite runner failed: {exception}", file=sys.stderr, flush=True)
        raise
