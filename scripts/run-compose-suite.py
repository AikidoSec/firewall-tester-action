import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys


RESULTS = Path(sys.argv[1])
COMPOSE = sys.argv[2:]


def compose(*arguments, **kwargs):
    return subprocess.run(COMPOSE + list(arguments), check=True, **kwargs)


def run_test(test_name):
    try:
        compose("start", test_name)
        result = subprocess.run(
            COMPOSE + ["exec", "-T", "suite-runner", "python", "run_suite.py", "--test", test_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode not in (0, 1) or not (RESULTS / f"{test_name}.json").is_file():
            raise RuntimeError(f"Test runner failed for {test_name}: {result.stdout}")
        return result.stdout
    finally:
        compose("stop", "--timeout", "10", test_name)


def main():
    tests = [name for name in os.environ["SUITE_TESTS"].split(",") if name]
    try:
        services = json.loads(compose("config", "--format", "json", stdout=subprocess.PIPE).stdout)["services"]
        required = set()
        pending = ["suite-runner", *tests]
        while pending:
            name = pending.pop()
            if name not in required:
                required.add(name)
                pending.extend(services[name].get("depends_on", {}))
        support = sorted(required - set(tests))
        compose(
            "up", "--detach", "--no-build", "--wait",
            "--wait-timeout", os.environ["STARTUP_TIMEOUT"], *support,
        )
        if tests:
            compose("up", "--no-start", "--no-build", "--no-deps", *tests)
            max_workers = min(len(tests), int(os.environ["SUITE_MAX_WORKERS"]))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(run_test, name) for name in tests]
                try:
                    for future in concurrent.futures.as_completed(futures):
                        print(future.result(), end="", flush=True)
                except BaseException:
                    for future in futures:
                        future.cancel()
                    raise
        running = compose("ps", "--status", "running", "--services", *support, stdout=subprocess.PIPE, text=True)
        if set(running.stdout.splitlines()) != set(support):
            raise RuntimeError("A supporting service stopped before the suite finished")
    finally:
        compose("logs", "--no-color")
    return subprocess.run(
        COMPOSE + ["exec", "-T", "suite-runner", "python", "run_suite.py", "--summarize"]
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
