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

CORE_URL = "http://localhost:3000"
DOCKER_IMAGE_NAME = "firewall-tester-action-docker-image"


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


@dataclass
class TestResult:
    test_dir: str
    start_time: datetime
    end_time: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None
    duration: Optional[float] = None

    def complete(self, success: bool, error_message: Optional[str] = None):
        self.end_time = datetime.now()
        self.success = success
        self.error_message = error_message
        self.duration = (self.end_time - self.start_time).total_seconds()


def run_test(test_dir: str, token: str, dockerfile_path: str, start_port: int, config_update_delay: int) -> TestResult:
    result = TestResult(test_dir=test_dir, start_time=datetime.now())
    try:
        # 1. if start_config.json exists, apply it
        core_api = CoreApi(token=token, core_url=CORE_URL,
                           config_update_delay=1)
        if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), test_dir, "start_config.json")):
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), test_dir, "start_config.json"), "r") as f:
                try:
                    config = json.load(f)
                    r = core_api.update_runtime_config_json(config)
                    logger.debug(f"Config: {r}")
                except Exception as e:
                    logger.error(
                        f"Error applying start_config.json: {e} \n{traceback.format_exc()}")
                    raise Exception(
                        f"Error applying start_config.json: {e} \n{traceback.format_exc()}")

        # 2. run the Docker container
        env_file_path = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), test_dir, 'test.env')
        if not os.path.exists(env_file_path):
            raise Exception(
                f"Env file not found: {env_file_path} for test: {test_dir}")
        command = (
            f"docker run -d "
            f"--network host "
            f"--env-file {env_file_path} "
            f"--env AIKIDO_TOKEN={token} "
            f"--env PORT={start_port} "
            f"--name {test_dir} "
            f"{DOCKER_IMAGE_NAME}"
        )
        logger.debug(f"Running Docker container: {command}")
        subprocess.run(command, shell=True, check=True)
        # 3. wait for the container to be ready
        time.sleep(1)
        server_tests_dir = os.path.dirname(os.path.abspath(__file__))
        # 4. run the test
        command = f"PYTHONPATH={server_tests_dir} python {os.path.join(server_tests_dir, test_dir, 'test.py')} --server_port {start_port} --token {token} --config_update_delay {config_update_delay} --core_port 3000"
        logger.debug(f"Running test: {command}")

        # Run the test and capture both stdout and stderr
        process = subprocess.run(
            command,
            shell=True,
            check=False,  # Don't raise exception on non-zero exit
            capture_output=True,
            text=True
        )

        if process.returncode != 0:
            # Extract the actual assertion error and stack trace from the output
            error_lines = process.stderr.split('\n')

            # Find the full assertion error message
            assertion_error = None
            for line in error_lines:
                if 'AssertionError:' in line:
                    assertion_error = line.strip()
                    break

            # Find the last stack trace line from test.py
            test_stack_line = None
            for line in reversed(error_lines):
                if 'test.py' in line and 'in run_test' in line:
                    test_stack_line = line.strip()
                    break

            if assertion_error and test_stack_line:
                error_message = f"{test_stack_line}<br>`{assertion_error}`"
                raise Exception(error_message)
            else:
                raise Exception(
                    f"Test failed with return code {process.returncode}\n```\n{process.stderr}\n```")

        result.complete(True)
        return result

    except Exception as e:
        logger.error(f"Error running test: {e}")
        result.complete(False, str(e))
        return result
    finally:
        # redirect logs of the docker container to > $GITHUB_STEP_SUMMARY
        # subprocess.run(f"docker logs {test_dir} 2>&1 >> $GITHUB_STEP_SUMMARY",
        #               shell=True, check=False, capture_output=True)
        # stop the container
        subprocess.run(f"docker stop {test_dir}",
                       shell=True, check=True, capture_output=True)
        # remove the container
        subprocess.run(f"docker rm -f {test_dir}",
                       shell=True, check=True, capture_output=True)


def build_docker_image(dockerfile_path: str):
    if not os.path.exists(dockerfile_path):
        raise Exception(f"Dockerfile not found: {dockerfile_path}")

    # Get the directory containing the Dockerfile
    dockerfile_dir = os.path.dirname(dockerfile_path)
    docker_build_command = f"docker build -t {DOCKER_IMAGE_NAME} -f {dockerfile_path} {dockerfile_dir}"
    logger.debug(f"Building Docker image: {docker_build_command}")
    subprocess.run(docker_build_command, shell=True, check=True)


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
            1 for r in test_results if r.success and r.error_message != "Skipped")
        skipped_tests = sum(
            1 for r in test_results if r.error_message == "Skipped")
        failed_tests = total_tests - passed_tests - skipped_tests
        total_duration = sum(
            r.duration for r in test_results if r.duration is not None)

        f.write("### Overview\n\n")
        f.write(f"- **Total Tests:** {total_tests}\n")
        f.write(f"- **Passed:** {passed_tests}\n")
        f.write(f"- **Skipped:** {skipped_tests}\n")
        f.write(f"- **Failed:** {failed_tests}\n")
        f.write(f"- **Total Duration:** {total_duration:.2f} seconds\n\n")

        # Write detailed results table
        f.write("### Detailed Results\n\n")
        f.write("| Test | Status | Duration | Error Message |\n")
        f.write("|------|--------|----------|---------------|\n")

        for result in test_results:
            if result.error_message == "Skipped":
                status = "⏭️ SKIP"
            else:
                status = "✅ PASS" if result.success else "❌ FAIL"
            duration = f"{result.duration:.2f}s" if result.duration is not None else "N/A"
            error = result.error_message if result.error_message else "-"
            # Escape pipe characters in error messages to prevent table formatting issues
            error = error.replace("|", "\\|")
            f.write(
                f"| {result.test_dir} | {status} | {duration} | {error} |\n")


def run_tests(dockerfile_path: str, max_parallel_tests: int, config_update_delay: int, skip_tests: str):
    logger.debug(f"Dockerfile path: {dockerfile_path}")
    logger.debug(f"Max parallel tests: {max_parallel_tests}")
    build_docker_image(dockerfile_path)

    test_dirs = [d for d in os.listdir(os.path.dirname(
        os.path.abspath(__file__))) if d.startswith("test_")]
    test_results: List[TestResult] = []

    # Parse skip_tests into a set for O(1) lookup
    tests_to_skip = set(skip_tests.split(',')) if skip_tests else set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel_tests) as executor:
        future_to_test = {}
        start_port = 3001

        for test_dir in test_dirs:
            # Skip tests that are in the skip list
            if test_dir in tests_to_skip:
                result = TestResult(test_dir=test_dir,
                                    start_time=datetime.now())
                result.complete(True, "Skipped")
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
                config_update_delay
            )
            future_to_test[future] = test_dir
            start_port += 1

        for future in concurrent.futures.as_completed(future_to_test):
            test_dir = future_to_test[future]
            try:
                result = future.result()
                test_results.append(result)
                status = "PASSED" if result.success else "FAILED"
                logger.info(
                    f"Test {test_dir} {status} in {result.duration:.2f} seconds")
                if not result.success:
                    logger.error(
                        f"Error in test {test_dir}: {result.error_message}")
            except Exception as e:
                logger.error(
                    f"Test {test_dir} generated an exception: {e} \n{traceback.format_exc()}")
                result = TestResult(test_dir=test_dir,
                                    start_time=datetime.now())
                result.complete(
                    False, f"{e} \n```\n{traceback.format_exc()}\n```")
                test_results.append(result)
                break

    # Write summary to GitHub Step Summary
    write_summary_to_github_step_summary(test_results)

    # Print summary to console as well
    logger.info("\nTest Summary:")
    logger.info("=" * 50)
    total_tests = len(test_results)
    passed_tests = sum(
        1 for r in test_results if r.success and r.error_message != "Skipped")
    skipped_tests = sum(
        1 for r in test_results if r.error_message == "Skipped")
    failed_tests = total_tests - passed_tests - skipped_tests
    total_duration = sum(
        r.duration for r in test_results if r.duration is not None)

    logger.info(f"Total Tests: {total_tests}")
    logger.info(f"Passed: {passed_tests}")
    logger.info(f"Skipped: {skipped_tests}")
    logger.info(f"Failed: {failed_tests}")
    logger.info(f"Total Duration: {total_duration:.2f} seconds")
    logger.info("=" * 50)

    # Exit with error if any tests failed
    if failed_tests > 0:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dockerfile_path", type=str, required=True)
    parser.add_argument("--max_parallel_tests", type=int, required=True)
    parser.add_argument("--config_update_delay", type=int, required=True)
    parser.add_argument("--skip_tests", type=str, required=False)
    args = parser.parse_args()
    run_tests(args.dockerfile_path, args.max_parallel_tests,
              args.config_update_delay, args.skip_tests)
