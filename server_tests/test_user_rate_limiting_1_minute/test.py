import requests
import time
import sys
from testlib import *
from core_api import CoreApi
import os


'''
1. Sets up the rate limiting config to 5 requests / minute for route '/'.
2. Sends 5 requests to '/'. Checks that those requests are not blocked.
3. Send another more 5 request to '/'. Checks that they all are rate limited.
4. Sends 100 requests to another route '/tests'. Checks that those requests are not blocked.
'''


def run_test(s: TestServer, c: CoreApi):
    for _ in range(5):
        response = s.get(
            "/",  headers={"X-Forwarded-For": "2.16.53.5"})
        assert_response_code_is(response, 200)

    # sleep for 10 seconds
    time.sleep(10)

    for i in range(10):
        response = s.get(
            "/", headers={"X-Forwarded-For": "2.16.53.5"})
        if i < 5:
            pass
        else:
            assert_response_code_is(response, 429)

    for _ in range(100):
        response = s.get(
            "/api/pets/", headers={"X-Forwarded-For": "2.16.53.5"})
        assert_response_code_is(response, 200)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
