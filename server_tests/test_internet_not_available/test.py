from testlib import *
from core_api import CoreApi


"""
1. Set up AIKIDO_BLOCK=1.
2. Set AIKIDO_ENDPOINT and AIKIDO_REALTIME_ENDPOINT to a non-existent IP.
3. Send a request to a route, that will cause sending a detection event.
4. Check that the attack was blocked.
"""


def run_test(s: TestServer, c: CoreApi):
    response = s.post("/api/execute", {"userCommand": "whoami"})
    assert_response_code_is(response, 500, response.text)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
