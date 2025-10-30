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
    response = s.get("/api/pets/",  headers={"X-Forwarded-For": "2.16.53.5"})
    assert_response_code_is(response, 200)
    response_body = response.json()
    assert isinstance(response_body, list)

    c.update_runtime_config_file("change_config_remove_bypassed_ip.json")

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "2.16.53.5"})
    assert_response_body_contains(response, "is blocked")
    assert_response_code_is(response, 403)

    c.update_runtime_config_file("start_config.json")

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "2.16.53.5"})
    assert_response_code_is(response, 200)
    response_body = response.json()
    assert isinstance(response_body, list)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
