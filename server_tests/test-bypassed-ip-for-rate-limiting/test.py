import requests
import time
import sys
from testlib import *
from core_api import CoreApi
import os


'''
1. Sets up the bypassed IP address config for route '/test'. Rate limiting is set to 10 req / min. Checks that requests are not rate limited blocked.
2. Changes the config to remove the bypassed IP address. Checks that requests are rate limiting.
3. Changes the config again to enable the bypassed IP address. Checks that requests are not rate limited blocked.
'''


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    for i in range(100):
        response = s.get(
            "/api/pets/",  headers={"X-Forwarded-For": "2.16.53.5"})
        collector.soft_assert_response_code_is(
            response, 200,
            f"Request {i + 1} from bypassed IP 2.16.53.5 should be allowed even past the route limit",
        )

    c.update_runtime_config_file("change_config_remove_bypassed_ip.json")

    for i in range(100):
        response = s.get(
            "/api/pets/", headers={"X-Forwarded-For": "2.16.53.5"})
        if i < 10:
            collector.soft_assert_response_code_is(
                response, 200,
                f"Request {i + 1} is within the 10-request limit after removing the IP bypass",
            )
        else:
            collector.soft_assert_response_code_is(
                response, 429, f"Request {i + 1} exceeds the 10-request limit after removing the IP bypass"
            )

    c.update_runtime_config_file("start_config.json")

    for i in range(100):
        response = s.get(
            "/api/pets/", headers={"X-Forwarded-For": "2.16.53.5"})
        collector.soft_assert_response_code_is(
            response, 200, f"Request {i + 1} from 2.16.53.5 should be allowed after restoring the IP bypass"
        )

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
