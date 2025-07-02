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


def f(config_file: str):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), config_file)


def run_test(s: TestServer, c: CoreApi):
    # Using global ts and c from testlib
    response = s.get("/api/pets/",
                     headers={"X-Forwarded-For": "1.3.3.7"})
    assert_response_body_contains(
        response, " not allowed ")
    assert_response_code_is(response, 403)
    assert_response_header_contains(response, "Content-Type", "text")

    c.update_runtime_config_file(f("change_config_remove_allowed_ip.json"))

    response = s.get("/api/pets/",
                     headers={"X-Forwarded-For": "1.3.3.7"})
    assert_response_body_contains(response, "[]")
    assert_response_code_is(response, 200)

    c.update_runtime_config_file(f("start_config.json"))

    response = s.get("/api/pets/",
                     headers={"X-Forwarded-For": "1.3.3.7"})
    assert_response_body_contains(
        response, " not allowed ")
    assert_response_code_is(response, 403)
    assert_response_header_contains(response, "Content-Type", "text")


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
