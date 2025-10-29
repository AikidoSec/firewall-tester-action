from testlib import *
from core_api import CoreApi


'''
1. Sets up a simple config and env AIKIDO_BLOCK=1 and AIKIDO_TOKEN is not set
2. Send some attacks and check that they are blocked (response code 500).
'''


def check_attacks_blocked(response_code):

    # sql injection
    response = s.post(
        "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"})
    assert_response_code_is(response, response_code, "sql injection")

    # shell injection
    response = s.post("/api/execute", {"userCommand": "whoami"})
    assert_response_code_is(response, response_code, "shell injection")

    # path traversal
    response = s.get("/api/read?path=../secrets/key.txt")
    assert_response_code_is(response, response_code, "path traversal")


def run_test(s: TestServer, c: CoreApi):
    check_attacks_blocked(500)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
