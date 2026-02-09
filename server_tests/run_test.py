import logging
import sys
import argparse
import traceback
import requests
import os
from core_api import CoreApi
import json
import subprocess
import time
import concurrent.futures
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from enum import Enum
import shlex
import re

CORE_URL = "http://localhost:3000"
DOCKER_IMAGE_NAME = "firewall-tester-action-docker-image"
# ip addr show docker0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1
DOCKER_HOST_IP = "172.17.0.1" if os.environ.get(
    "GITHUB_ACTIONS") == "true" else "172.18.0.1"


class GitHubActionsFormatter(logging.Formatter):
    def format(self, record):
        level = record.levelname.lower()
        message = super().format(record)

        if record.levelno == logging.ERROR:
            return f"::error::{message}"
        elif record.levelno == logging.WARNING:
            return f"::warning::{message}"
        elif record.levelno == logging.INFO:
            return f"{message}"
        elif record.levelno == logging.DEBUG:
            return f"::debug::{message}"
        else:
            return message


def get_logger(name: str = "github_actions_logger") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        handler = logging.StreamHandler(sys.stdout)
        formatter = GitHubActionsFormatter(
            "%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger


logger = get_logger()


class TestStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    TIMEOUT = "TIMEOUT"


@dataclass
class TestResult:
    test_dir: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TestStatus = TestStatus.FAILED
    error_message: Optional[str] = None
    duration: Optional[float] = None
    failed_assertions: Optional[List[str]] = None

    def complete(self, status: TestStatus, error_message: Optional[str] = None):
        self.end_time = datetime.now()
        self.status = status
        self.error_message = error_message
        self.duration = (self.end_time - self.start_time).total_seconds()


def sanitize_extra_run_args(extra_args: str):
    allowed_prefixes = ("--env", "-e", "--env-file")
    result = []

    if not extra_args:
        return ""

    args = shlex.split(extra_args)

    i = 0
    while i < len(args):
        arg = args[i]

        if arg.startswith(allowed_prefixes):
            # Handle both "--env=VAR=value" and "--env VAR=value"
            if "=" in arg:
                # Single argument form: --env=VAR=value or -e=VAR=value
                if arg.startswith("--env-file="):
                    # Convert relative path to absolute path for --env-file
                    file_path = arg.split("=", 1)[1]
                    abs_path = os.path.abspath(file_path)
                    result.append(f"--env-file={abs_path}")
                else:
                    result.append(arg)
            else:
                # Separate form: --env VAR=value or -e VAR=value
                if i + 1 >= len(args):
                    raise ValueError(f"Missing value for {arg}")
                value = args[i + 1]
                if arg == "--env-file":
                    # Convert relative path to absolute path for --env-file
                    abs_path = os.path.abspath(value)
                    result.extend([arg, abs_path])
                else:
                    result.extend([arg, value])
                i += 1
        else:
            raise ValueError(f"Disallowed argument: {arg}")

        i += 1

    return " ".join(result)


def run_test(test_dir: str, token: str, dockerfile_path: str, start_port: int, config_update_delay: int, test_timeout: int, extra_args: str, app_port: int, sleep_before_test: int, control_port: int) -> TestResult:
    result = TestResult(test_dir=test_dir, start_time=datetime.now())
    try:
        # 1. if start_config.json and start_firewall.json exists, apply them
        core_api = CoreApi(token=token, core_url=CORE_URL, test_name=test_dir,
                           config_update_delay=1)
        if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), test_dir, "start_config.json")):
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), test_dir, "start_config.json"), "r") as f:
                try:
                    config = json.load(f)
                    r = core_api.update_runtime_config_json(config)
                except Exception as e:
                    logger.error(
                        f"Error applying start_config.json: {e} \n{traceback.format_exc()}")
                    raise Exception(
                        f"Error applying start_config.json: {e} \n{traceback.format_exc()}")

        if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), test_dir, "start_firewall.json")):
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), test_dir, "start_firewall.json"), "r") as f:
                try:
                    config = json.load(f)
                    r = core_api.update_runtime_firewall_json(config)
                except Exception as e:
                    logger.error(
                        f"Error applying start_firewall.json: {e} \n{traceback.format_exc()}")
                    raise Exception(
                        f"Error applying start_firewall.json: {e} \n{traceback.format_exc()}")

        # 2. run the Docker container
        create_database_command = f"docker exec postgres createdb -U myuser {test_dir}"
        subprocess.run(create_database_command, shell=True, check=True)
        time.sleep(1)

        extra_envs = {
            "AIKIDO_TOKEN": token,
            "PORT": app_port,
            "DATABASE_URL": f"postgres://myuser:mysecretpassword@{DOCKER_HOST_IP}:5432/{test_dir}?sslmode=disable",
            "AIKIDO_ENDPOINT": f"http://{DOCKER_HOST_IP}:3000",
            "AIKIDO_REALTIME_ENDPOINT": f"http://{DOCKER_HOST_IP}:3000",
            "AIKIDO_URL": f"http://{DOCKER_HOST_IP}:3000",
            "AIKIDO_REALTIME_URL": f"http://{DOCKER_HOST_IP}:3000",
        }
        env_file_path = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), test_dir, 'test.env')
        if os.path.exists(env_file_path):
            # remove from extra_envs env that are already in the file
            with open(env_file_path, "r") as f:
                content = f.read()
            keys_to_remove = [
                env for env in extra_envs if f"{env}=" in content]
            for env in keys_to_remove:
                del extra_envs[env]

        command = (
            f"docker run -d "
            f"{sanitize_extra_run_args(extra_args)} "
            f"--env-file {env_file_path} "
            f"--name {test_dir} "
            f"-p {start_port}:{app_port} "
        )

        if control_port:
            command += f" -p {control_port}:8081 "

        for env, value in extra_envs.items():
            command += f" --env {env}={value}"
        command += f" {DOCKER_IMAGE_NAME}"

        logger.debug(f"Running Docker container: {command}")
        subprocess.run(command, shell=True, check=True)
        # 3. wait for the container to be ready
        time.sleep(sleep_before_test)

        # 4. Cold turkey :
        # Cold turkey for python
        if not control_port:
            try:
                requests.get(f"http://localhost:{start_port}/")
            except Exception as e:
                logger.error(
                    f"Error getting server: {e} \n{traceback.format_exc()}")
            time.sleep(1)

        server_tests_dir = os.path.dirname(os.path.abspath(__file__))
        # 5. run the test
        command = f"PYTHONPATH={server_tests_dir} python {os.path.join(server_tests_dir, test_dir, 'test.py')} --test_name {test_dir} --server_port {start_port} --token {token} --config_update_delay {config_update_delay} --core_port 3000"
        if control_port:
            command += f" --control_server_port {control_port}"
        logger.debug(f"Running test: {command}")

        # Run the test with timeout
        try:
            process = subprocess.run(
                command,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=test_timeout
            )

            # Log test output
            if process.stdout:
                logger.debug(
                    f"{'-'*20}[{test_dir} :stdout] {'-'*20}:\n{process.stdout} \n{'-'*50}")
            if process.stderr:
                logger.debug(
                    f"{'-'*30}[{test_dir} :stderr] {'-'*30}:\n{process.stderr} \n{'-'*100}")

            if process.returncode != 0:
                # Extract the actual assertion error and stack trace from the output
                error_lines = process.stderr.split('\n')

                # Extract individual [FAIL] markers for soft assertion failures
                failed_assertions = []
                for line in error_lines:
                    stripped = line.strip()
                    if stripped.startswith("[FAIL]"):
                        failed_assertions.append(stripped[len("[FAIL] "):])
                result.failed_assertions = failed_assertions if failed_assertions else None

                # Find the full assertion error message (may be multi-line for soft assertions)
                assertion_error = None
                assertion_start_idx = None
                for i, line in enumerate(error_lines):
                    if 'AssertionError:' in line:
                        assertion_start_idx = i
                        break

                if assertion_start_idx is not None:
                    assertion_lines = []
                    for i in range(assertion_start_idx, len(error_lines)):
                        stripped = error_lines[i].strip()
                        if stripped:
                            assertion_lines.append(stripped)
                    assertion_error = "\n".join(assertion_lines)

                # Find the last stack trace line from test.py
                test_stack_line = None
                for i in range(len(error_lines)):
                    line = error_lines[i]
                    if f'{test_dir}/test.py' in line:
                        test_stack_line = line.strip()

                if assertion_error and test_stack_line:
                    if failed_assertions:
                        error_message = (
                            f"{len(failed_assertions)} assertion(s) failed<br>"
                            + "<br>".join(
                                f"`{fa}`" for fa in failed_assertions
                            )
                        )
                    else:
                        error_message = f"{test_stack_line}<br>`{assertion_error}`"
                    raise Exception(error_message)
                else:
                    raise Exception(
                        f"Test failed with return code {process.returncode}\n```\n{process.stderr}\n```")

            result.complete(TestStatus.PASSED)
            return result

        except subprocess.TimeoutExpired:
            result.complete(TestStatus.TIMEOUT,
                            f"Test timed out after {test_timeout} seconds")
            return result

    except Exception as e:
        logger.error(f"Error running test: {e}")
        result.complete(TestStatus.FAILED, str(e))
        return result
    finally:
        # chcek the logs for "Segmentation fault" or "core dumped"
        logs_str = ""
        logs = None
        try:
            logs = subprocess.check_output(
                ["docker", "logs", test_dir], stderr=subprocess.STDOUT)
            logs_str = logs.decode("utf-8")
            logger.debug(f"Logs: {logs_str}")
        except Exception as e:
            logger.error(f"Error getting logs: {e} \n{traceback.format_exc()}")
            logs_str = ""

        if "Segmentation fault" in logs_str or "core dumped" in logs_str:
            result.complete(TestStatus.FAILED,
                            "Segmentation fault or core dumped")
            return result

        # stop the container
        subprocess.run(f"docker stop {test_dir}",
                       shell=True, check=False, capture_output=False)
        # remove the container
        subprocess.run(f"docker rm -f {test_dir}",
                       shell=True, check=False, capture_output=False)


def build_docker_image(dockerfile_path: str, extra_build_args: str):
    if not os.path.exists(dockerfile_path):
        # list files from dockerfile_path root
        logger.debug(f"Dockerfile not found: {dockerfile_path}")
        logger.debug(
            f"Files in {os.path.dirname(dockerfile_path)}: {os.listdir(os.path.dirname(dockerfile_path))}")
        raise Exception(f"Dockerfile not found: {dockerfile_path}")

    # Get the directory containing the Dockerfile
    dockerfile_dir = os.path.dirname(dockerfile_path)
    command = ["docker", "build", "-t",
               DOCKER_IMAGE_NAME, "-f", dockerfile_path]
    if extra_build_args:
        try:
            # extra_build_args is a string of arguments separated by spaces (e.g. "--build-arg APP_VERSION=2.0.1 --build-arg PHP_FIREWALL_VERSION=1.0.123")
            command.extend(extra_build_args.split(" "))
        except ValueError as e:
            print(f"Invalid build args: {e}")
            return

    command.append(dockerfile_dir)
    logger.debug(f"Building Docker image: {' '.join(command)}")
    subprocess.run(" ".join(command), shell=True, check=True)


def _linkify_line_ref(text: str, test_dir: str) -> str:
    """Replace [line X → line Y → ...] prefix with clickable GitHub links."""
    def _make_link(line_num: str) -> str:
        url = f"https://github.com/AikidoSec/firewall-tester-action/blob/main/server_tests/{test_dir}/test.py#L{line_num}"
        return f"[line {line_num}]({url})"

    # Match the entire bracket prefix: [line N] or [line N → line M → ...]
    bracket_match = re.match(r'\[(line \d+(?:\s*→\s*line \d+)*)\]\s*', text)
    if bracket_match:
        inner = bracket_match.group(1)
        # Replace each "line N" with a link
        linked = re.sub(r'line (\d+)', lambda m: _make_link(m.group(1)), inner)
        text = linked + " " + text[bracket_match.end():]
    return text


def _get_source_context(test_dir: str, assertion_text: str, context_lines: int = 3) -> Optional[str]:
    """Extract lines around each failure frame from test.py (context_lines before + the line + context_lines after)."""
    line_nums = [int(m) for m in re.findall(r'line (\d+)', assertion_text)]
    if not line_nums:
        return None
    test_file = os.path.join(os.path.dirname(__file__), test_dir, "test.py")
    try:
        with open(test_file, 'r') as f:
            lines = f.readlines()
        snippets = []
        for line_num in line_nums:
            start = max(0, line_num - 1 - context_lines)
            end = min(len(lines), line_num + context_lines)
            snippet_lines = []
            for i in range(start, end):
                marker = "→" if (i + 1) == line_num else " "
                snippet_lines.append(
                    f"{marker} {i + 1:>4} | {lines[i].rstrip()}")
            snippets.append("\n".join(snippet_lines))
        return "\n\n".join(snippets)
    except Exception:
        return None


def write_summary_to_github_step_summary(test_results: List[TestResult]):
    summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
    if not summary_path:
        logger.warning("GITHUB_STEP_SUMMARY environment variable not set")
        return

    with open(summary_path, 'a') as f:
        f.write("\n## Test Results Summary\n\n")

        # Write summary statistics
        total_tests = len(test_results)
        passed_tests = sum(
            1 for r in test_results if r.status == TestStatus.PASSED)
        skipped_tests = sum(
            1 for r in test_results if r.status == TestStatus.SKIPPED)
        timeout_tests = sum(
            1 for r in test_results if r.status == TestStatus.TIMEOUT)
        failed_tests = sum(
            1 for r in test_results if r.status == TestStatus.FAILED)

        f.write("### Overview\n\n")
        f.write(f"- **Total Tests:** {total_tests}\n")
        f.write(f"- **Passed:** {passed_tests}\n")
        f.write(f"- **Skipped:** {skipped_tests}\n")
        f.write(f"- **Timed Out:** {timeout_tests}\n")
        f.write(f"- **Failed:** {failed_tests}\n")

        # Write detailed results table
        f.write("### Detailed Results\n\n")
        f.write("| Test | Status | Duration | Error Message |\n")
        f.write("|------|--------|----------|---------------|\n")

        for result in test_results:
            status_emoji = {
                TestStatus.PASSED: "✅ PASS",
                TestStatus.FAILED: "❌ FAIL",
                TestStatus.SKIPPED: "⏭️ SKIP",
                TestStatus.TIMEOUT: "⏰ TIMEOUT"
            }
            status = status_emoji[result.status]
            duration = f"{result.duration:.2f}s" if result.duration is not None else "N/A"
            if result.failed_assertions:
                error = f"{len(result.failed_assertions)} assertion(s) failed (see details below)"
            elif result.error_message:
                error = result.error_message
            else:
                error = "-"
            # Escape pipe characters in error messages to prevent table formatting issues
            error = error.replace("|", "\\|")
            f.write(
                f"| {result.test_dir} | {status} | {duration} | {error} |\n")

        # Write detailed failure information for tests with multiple assertion failures
        failed_with_details = [
            r for r in test_results if r.failed_assertions]
        if failed_with_details:
            f.write("\n### Failed Assertions Details\n\n")
            for result in failed_with_details:
                f.write(f"<details>\n")
                f.write(
                    f"<summary>{result.test_dir} - {len(result.failed_assertions)} failed assertion(s)</summary>\n\n")
                for i, assertion in enumerate(result.failed_assertions, 1):
                    escaped = assertion.replace("|", "\\|")
                    escaped = _linkify_line_ref(escaped, result.test_dir)
                    f.write(f"{i}. {escaped}\n")
                    snippet = _get_source_context(result.test_dir, assertion)
                    if snippet:
                        f.write(f"   <details>\n")
                        f.write(f"   <summary>Show source</summary>\n\n")
                        f.write(f"   ```python\n")
                        for snippet_line in snippet.split("\n"):
                            f.write(f"   {snippet_line}\n")
                        f.write(f"   ```\n")
                        f.write(f"   </details>\n")
                f.write(f"\n</details>\n\n")


def run_tests(dockerfile_path: str, max_parallel_tests: int, config_update_delay: int, skip_tests: str, run_tests: str, test_timeout: int, extra_args: str, extra_build_args: str, app_port: int, sleep_before_test: int, ignore_failures: bool = False, test_type: str = "server"):
    logger.debug(f"Dockerfile path: {dockerfile_path}")
    logger.debug(f"Max parallel tests: {max_parallel_tests}")
    build_docker_image(dockerfile_path, extra_build_args)
    if test_type == "control":
        dir_start = "control_"
    else:
        dir_start = "test_"

    test_dirs = [d for d in os.listdir(os.path.dirname(
        os.path.abspath(__file__))) if d.startswith(dir_start)]
    test_results: List[TestResult] = []

    # Parse skip_tests into a set for O(1) lookup
    tests_to_skip = set(skip_tests.split(',')) if skip_tests else set()

    # Parse run_tests into a set for O(1) lookup
    tests_to_run = set(run_tests.split(',')) if run_tests else set()

    # If run_tests is specified, filter test_dirs to only include those tests
    if tests_to_run:
        test_dirs = [d for d in test_dirs if d in tests_to_run]

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel_tests) as executor:
        future_to_test = {}
        start_port = 3001
        control_start_port = 9001

        for test_dir in test_dirs:
            # Skip tests that are in the skip list
            if test_dir in tests_to_skip:
                result = TestResult(test_dir=test_dir,
                                    start_time=datetime.now())
                result.complete(TestStatus.SKIPPED, "Skipped")
                test_results.append(result)
                logger.info(f"Test {test_dir} ⏭️ SKIPPED")
                continue

            token = CoreApi.get_app_token(CORE_URL)
            future = executor.submit(
                run_test,
                test_dir,
                token,
                dockerfile_path,
                start_port,
                config_update_delay,
                test_timeout,
                extra_args,
                app_port,
                sleep_before_test,
                None if test_type == "server" else control_start_port

            )
            future_to_test[future] = test_dir
            start_port += 1
            control_start_port += 1

        for future in concurrent.futures.as_completed(future_to_test):
            test_dir = future_to_test[future]
            try:
                result = future.result()
                test_results.append(result)
                status_emoji = {
                    TestStatus.PASSED: "✅ PASSED",
                    TestStatus.FAILED: "❌ FAILED",
                    TestStatus.SKIPPED: "⏭️ SKIPPED",
                    TestStatus.TIMEOUT: "⏰ TIMED OUT"
                }
                logger.info(
                    f"Test {test_dir} {status_emoji[result.status]} in {result.duration:.2f} seconds")
                if result.status == TestStatus.FAILED:
                    logger.error(
                        f"Error in test {test_dir}: {result.error_message}")
            except Exception as e:
                logger.error(
                    f"Test {test_dir} generated an exception: {e} \n{traceback.format_exc()}")
                result = TestResult(test_dir=test_dir,
                                    start_time=datetime.now())
                result.complete(
                    TestStatus.FAILED, f"{e} \n```\n{traceback.format_exc()}\n```")
                test_results.append(result)
                break

    # Write summary to GitHub Step Summary
    write_summary_to_github_step_summary(test_results)

    # Print summary to console as well
    logger.info("\nTest Summary:")
    logger.info("=" * 50)
    total_tests = len(test_results)
    passed_tests = sum(
        1 for r in test_results if r.status == TestStatus.PASSED)
    skipped_tests = sum(
        1 for r in test_results if r.status == TestStatus.SKIPPED)
    timeout_tests = sum(
        1 for r in test_results if r.status == TestStatus.TIMEOUT)
    failed_tests = sum(
        1 for r in test_results if r.status == TestStatus.FAILED)
    total_duration = sum(
        r.duration for r in test_results if r.duration is not None)

    logger.info(f"Total Tests: {total_tests}")
    logger.info(f"Passed: {passed_tests}")
    logger.info(f"Skipped: {skipped_tests}")
    logger.info(f"Timed Out: {timeout_tests}")
    logger.info(f"Failed: {failed_tests}")
    logger.info(f"Total Duration: {total_duration:.2f} seconds")
    logger.info("=" * 50)

    # Exit with error if any tests failed or timed out
    if failed_tests > 0 or timeout_tests > 0:
        if ignore_failures == "true":
            logger.warning("Tests failed but ignoring failures as requested")
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dockerfile_path", type=str, required=True)
    parser.add_argument("--max_parallel_tests", type=int, required=True)
    parser.add_argument("--config_update_delay", type=int, required=True)
    parser.add_argument("--skip_tests", type=str, required=False)
    parser.add_argument("--run_tests", type=str, required=False)
    parser.add_argument("--test_timeout", type=int, required=False)
    parser.add_argument("--extra_args", type=str, required=False)
    parser.add_argument("--extra_build_args", type=str, required=False)
    parser.add_argument("--app_port", type=int, required=False)
    parser.add_argument("--sleep_before_test", type=int, required=False)
    parser.add_argument("--ignore_failures", type=str,
                        required=False, default="false")
    parser.add_argument("--test_type", type=str,
                        required=False, default="server")

    args = parser.parse_args()
    run_tests(args.dockerfile_path, args.max_parallel_tests,
              args.config_update_delay, args.skip_tests, args.run_tests or '', args.test_timeout, args.extra_args, args.extra_build_args, args.app_port, args.sleep_before_test, args.ignore_failures, args.test_type)
