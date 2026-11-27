import requests
import time
import sys
from testlib import *
from core_api import CoreApi
import os


'''
1. Sets up the allowed IP address config for route '/test'. Checks that requests are blocked.
2. Changes the config to remove the allowed IP address. Checks that requests are passing.
3. Changes the config again to enable allowed IP address. Checks that requests are blocked.
'''


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    response = s.get("/api/pets/",  headers={"X-Forwarded-For": "2.16.53.5"})
    collector.soft_assert_response_code_is(
        response, 200, "The bypass list should allow 2.16.53.5 despite the country block"
    )
    if response.status_code == 200:
        response_body = response.json()
        collector.soft_assert(isinstance(response_body, list),
                              "Response body should be a list")

    c.update_runtime_config_file("change_config_remove_bypassed_ip.json")

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "2.16.53.5"})
    collector.soft_assert_response_body_contains(
        response, "is blocked",
        "Removing 2.16.53.5 from the bypass list should produce a country-block response",
    )
    collector.soft_assert_response_code_is(
        response, 403, "The country block should apply after removing 2.16.53.5 from the bypass list"
    )

    c.update_runtime_config_file("start_config.json")

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "2.16.53.5"})
    collector.soft_assert_response_code_is(
        response, 200, "Restoring the bypass list should allow 2.16.53.5 again"
    )
    if response.status_code == 200:
        response_body = response.json()
        collector.soft_assert(isinstance(response_body, list),
                              "Response body should be a list")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
