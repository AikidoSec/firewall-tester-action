from testlib import *
from core_api import CoreApi


"""
1. Set up AIKIDO_BLOCK=1.
2. Set AIKIDO_ENDPOINT and AIKIDO_REALTIME_ENDPOINT to a non-existent IP.
3. Send a request to a route, that will cause sending a detection event.
4. Check that the attack was blocked.
"""


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()
    deadline = time.monotonic() + 90
    response = None

    while time.monotonic() < deadline:
        response = s.post("/api/execute", {"userCommand": "whoami"})
        if get_response_status_code(response) == 500:
            break
        time.sleep(2)

    collector.soft_assert_response_code_is(
        response,
        500,
        f"Agent did not start blocking before timeout. Last response: {response.text if response else 'no response'}",
    )
    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
