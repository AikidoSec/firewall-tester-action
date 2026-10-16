from testlib import *
from core_api import CoreApi


'''
1. Sets up a simple config and env AIKIDO_BLOCK=1 and AIKIDO_TOKEN= invalid token
2. Send some attacks and check that they are blocked (response code 500).
'''


def check_attacks_blocked(collector, s, response_code):

    # sql injection
    response = s.post(
        "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"})
    collector.soft_assert_response_code_is(response, response_code, "sql injection")

    # shell injection
    response = s.post("/api/execute", {"userCommand": "whoami"})
    collector.soft_assert_response_code_is(response, response_code, "shell injection")

    # path traversal
    response = s.get("/api/read?path=../secrets/key.txt")
    collector.soft_assert_response_code_is(response, response_code, "path traversal")


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()
    check_attacks_blocked(collector, s, 500)
    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
