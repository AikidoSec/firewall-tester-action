
from testlib import *
from core_api import CoreApi


"""
1 Start server with aikido installed
2. Send 100 requests and 100 attacks - blocked
3. Stop server, uninstall aikido, start server
4. Send 100 requests and 100 attacks - not blocked
5. Install aikido, send 100 attacks - not blocked
6. Restart server, send 100 attacks - blocked
"""


def send_100_requests():
    for _ in range(5):
        response = s.get("/api/pets/", retries=1)
        assert_response_code_is(response, 200,
                                f"Request failed: {response.text} {cs.get_server_logs()}")


def send_100_attacks(expected_code: int, expected_message: str):
    # path traversal attacks
    for _ in range(25):
        response = s.get("/api/read?path=../secrets/key.txt")
        assert_response_code_is(response, expected_code,
                                f"Request failed: {response.text} {cs.get_server_logs()}")
        assert_response_body_contains(
            response, expected_message, f"{response.text} {cs.get_server_logs()}")

    # sql injection attacks
    for _ in range(25):
        response = s.post(
            "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"})
        assert_response_code_is(response, expected_code,
                                f"Request failed: {response.text} {cs.get_server_logs()}")
        assert_response_body_contains(
            response, expected_message, f"{response.text} {cs.get_server_logs()}")

    # shell injection attacks
    for _ in range(25):
        response = s.post("/api/execute", {"userCommand": "whoami"})
        assert_response_code_is(response, expected_code,
                                f"Request failed: {response.text} {cs.get_server_logs()}")
        assert_response_body_contains(
            response, expected_message, f"{response.text} {cs.get_server_logs()}")

    # ssrf attacks
    for _ in range(25):
        response = s.post(
            "/api/request", {"url": "http://127.0.0.1:8081/health"}, timeout=10)
        assert_response_code_is(response, expected_code,
                                f"Request failed: {response.text} {cs.get_server_logs()}")
        assert_response_body_contains(
            response, expected_message, f"{response.text} {cs.get_server_logs()}")


def run_test(s: TestServer, c: CoreApi, cs: TestControlServer):
    # Start with aikido installed
    cs.check_health()
    cs.start_server()

    send_100_requests()
    send_100_attacks(500, "firewall has blocked")

    cs.stop_server()
    cs.uninstall_aikido()
    cs.start_server()

    send_100_requests()
    send_100_attacks(200, "")

    cs.install_aikido()
    send_100_attacks(200, "")

    cs.graceful_restart()
    send_100_attacks(500, "firewall has blocked")


if __name__ == "__main__":
    args, s, c, cs = init_server_and_core()
    run_test(s, c, cs)
