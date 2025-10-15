
from testlib import *
from core_api import CoreApi


"""
uninstall aikido
install old version
start server
100 attacks - blocked
100 requests

stop server
install current version
start server
100 attacks - blocked
100 requests
check events for new versions 

stop server
uninstall aikido
start server
100 attacks - not blocked
"""


"""
1. Install an old Aikido version + start server
2. Save started event 
3. Send 100 requests and 100 attacks - blocked
4. Stop server, install current version, start server
5. Save started event 
6. Compare versions to assert they are different (update successful)
7. Send 100 requests and 100 attacks - blocked
8. Stop server, uninstall aikido, start server
9. Send 100 requests and 100 attacks - not blocked
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
    cs.check_health()
    cs.uninstall_aikido()
    cs.install_aikido_version("1.3.5")
    cs.start_server()
    old_start_events = c.get_events("started")
    assert_events_length_is(old_start_events, 1)
    send_100_requests()
    send_100_attacks(500, "firewall has blocked")

    cs.stop_server()
    cs.install_aikido()
    cs.start_server()
    current_start_events = c.get_events("started")
    assert_events_length_is(current_start_events, 1)

    assert old_start_events[0]["agent"]["version"] != current_start_events[0]["agent"][
        "version"], f"Old version: {old_start_events[0]['agent']['version']} must be different from current version: {current_start_events[0]['agent']['version']}"

    send_100_requests()
    send_100_attacks(500, "firewall has blocked")

    cs.stop_server()
    cs.uninstall_aikido()
    cs.start_server()

    send_100_attacks(200, "")


if __name__ == "__main__":
    args, s, c, cs = init_server_and_core()
    run_test(s, c, cs)
