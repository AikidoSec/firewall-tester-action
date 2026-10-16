import requests
import time
import sys
from testlib import *
from core_api import CoreApi
import os


'''
1. Sets up the allowed IP address config for route '/test'. Checks that requests are blocked.
2. Changes the config to remote the allowed IP address. Checks that requests are passing.
3. Changes the config again to enable allowed IP address. Checks that requests are blocked.
'''


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    response = s.get("/api/pets/",
                     headers={"X-Forwarded-For": "1.3.3.7"})
    collector.soft_assert_response_code_is(response, 403)
    collector.soft_assert_response_body_contains(
        response, " not allowed ")

    c.update_runtime_config_file("change_config_remove_allowed_ip.json")

    response = s.get("/api/pets/",
                     headers={"X-Forwarded-For": "1.3.3.7"})
    collector.soft_assert_response_code_is(response, 200)
    if response.status_code == 200:
        response_body = response.json()
        collector.soft_assert(isinstance(response_body, list), "Response body should be a list")

    c.update_runtime_config_file("start_config.json")

    response = s.get("/api/pets/",
                     headers={"X-Forwarded-For": "1.3.3.7"})
    collector.soft_assert_response_code_is(response, 403)
    collector.soft_assert_response_body_contains(
        response, " not allowed ")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
