from testlib import *
from core_api import CoreApi


def run_test(s: TestServer, c: CoreApi):
    response = s.post("/api/execute", {"userCommand": "whoami"})
    assert_response_code_is(response, 500, response.text)

    c.set_mock_server_down()
    time.sleep(120)
    response = s.post("/api/execute", {"userCommand": "whoami"})
    assert_response_code_is(response, 500, response.text)

    for _ in range(5):
        response = s.get("/test_ratelimiting_1")
        assert_response_code_is(response, 200, response.text)

    time.sleep(10)

    for _ in range(5):
        response = s.get("/test_ratelimiting_1")
        assert_response_code_is(response, 429, response.text)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
