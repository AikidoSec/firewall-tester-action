import logging
import sys
import argparse
import requests
import os
from core_api import CoreApi
import json
import subprocess
import time

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
        formatter = GitHubActionsFormatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)  
    return logger

logger = get_logger()


def run_test(test_dir: str, token: str, dockerfile_path: str, start_port: int):
  try:
    # 1. if start_config.json exists, apply it
    core_api = CoreApi(token)
    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), test_dir, "start_config.json")):
      with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), test_dir, "start_config.json"), "r") as f:
        config = json.load(f)
        core_api.update_runtime_config(CORE_URL, config)
        logger.debug(f"Applied start_config.json")

    # 2. run the Docker container
    command = f"docker run -d --env-file {os.path.join(os.path.dirname(os.path.abspath(__file__)), test_dir, "test.env")} --env AIKIDO_TOKEN={token} -p {start_port}:3000 --name {test_dir} {DOCKER_IMAGE_NAME}"
    logger.debug(f"Running Docker container: {command}")
    subprocess.run(command, shell=True, check=True)
    # 3. wait for the container to be ready
    time.sleep(1)

    # 4. TODO: run the test


  except Exception as e:
    logger.error(f"Error running test: {e}")
    raise e
  finally:
    # stop the container 
    subprocess.run(f"docker stop {test_dir}", shell=True, check=True, capture_output=True)
    # remove the container
    subprocess.run(f"docker rm -f {test_dir}", shell=True, check=True, capture_output=True)

 
def build_docker_image(dockerfile_path: str):
  if not os.path.exists(dockerfile_path):
    raise Exception(f"Dockerfile not found: {dockerfile_path}")
  
  # Get the directory containing the Dockerfile
  dockerfile_dir = os.path.dirname(dockerfile_path)
  docker_build_command = f"docker build -t {DOCKER_IMAGE_NAME} -f {dockerfile_path} {dockerfile_dir}"
  logger.debug(f"Building Docker image: {docker_build_command}")
  subprocess.run(docker_build_command, shell=True, check=True)

def run_tests(dockerfile_path: str, max_parallel_tests: int):
    logger.debug(f"Dockerfile path: {dockerfile_path}")
    logger.debug(f"Max parallel tests: {max_parallel_tests}")
    build_docker_image(dockerfile_path)
    start_port = 3001
    for test_dir in os.listdir(os.path.dirname(os.path.abspath(__file__))):
      if test_dir.startswith("test_"):
        logger.debug(f"Running test: {test_dir}")
        token = CoreApi.get_app_token(CORE_URL)
        run_test(test_dir, token, dockerfile_path, start_port)
        start_port += 1


if __name__ == "__main__":
  
  parser = argparse.ArgumentParser()
  parser.add_argument("--dockerfile_path", type=str, required=True)
  parser.add_argument("--max_parallel_tests", type=int, required=True)
  args = parser.parse_args()
  run_tests(args.dockerfile_path, args.max_parallel_tests)
