
from testlib import *
from core_api import CoreApi


def run_test(s: TestServer, c: CoreApi, cs: TestControlServer):
    health = cs.health()
    assert_response_code_is(health, 200, f"Health check failed: {health.text}")

    start_server = cs.start_server()
    assert_response_code_is(
        start_server, 200, f"Start server failed: {start_server.text}")
    time.sleep(3)

    response = s.get("/api/read?path=../secrets/key.txt")
    assert_response_code_is(response, 500,
                            f"Path traversal check failed {response.text}")
    assert_response_body_contains(
        response, "firewall has blocked a path traversal", f"Path traversal check failed {response.text}")

    graceful_restart = cs.graceful_restart()
    assert_response_code_is(graceful_restart, 200,
                            f"Graceful restart failed: {graceful_restart.text}")
    time.sleep(3)

    status = cs.status()
    assert_response_code_is(status, 200,
                            f"Status check failed: {status.text} {cs.get_server_logs()}")
    assert_response_body_contains(
        status, "running", f"Server is not running {status.text} {cs.get_server_logs()}")

    response = s.get("/api/read?path=../secrets/key.txt")
    assert_response_code_is(response, 500,
                            f"Path traversal check failed after graceful restart {response.text} {cs.get_server_logs()}")
    assert_response_body_contains(
        response, "firewall has blocked a path traversal", f"Path traversal check failed after graceful restart {response.text} {cs.get_server_logs()}")


if __name__ == "__main__":
    args, s, c, cs = init_server_and_core()
    run_test(s, c, cs)
