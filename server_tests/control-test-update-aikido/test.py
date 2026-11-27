
from testlib import *
from core_api import CoreApi


"""
1. Install an old Aikido version + start server
2. Save started event
3. Send 100 requests and 8 attacks - blocked
4. Stop server, install current version, start server
5. Save started event
6. Compare versions to assert they are different (update successful)
7. Send 100 requests and 8 attacks - blocked
8. Stop server, uninstall aikido, start server
9. Send 100 requests and 8 attacks - not blocked
"""


def send_100_requests(collector):
    for _ in range(5):
        response = s.get("/api/pets/")
        collector.soft_assert_response_code_is(response, 200,
                                               f"Request failed: {response.text} {cs.get_server_logs()}")


def send_attacks(collector, expected_code: int, expected_message: str):
    # path traversal attacks
    for _ in range(2):
        response = s.get("/api/read?path=../secrets/key.txt")
        collector.soft_assert_response_code_is(response, expected_code,
                                               f"Request failed: {response.text} {cs.get_server_logs()}")
        collector.soft_assert_response_body_contains(
            response, expected_message, f"{response.text} {cs.get_server_logs()}")

    # sql injection attacks
    for _ in range(2):
        response = s.post(
            "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"})
        collector.soft_assert_response_code_is(response, expected_code,
                                               f"Request failed: {response.text} {cs.get_server_logs()}")
        collector.soft_assert_response_body_contains(
            response, expected_message, f"{response.text} {cs.get_server_logs()}")

    # shell injection attacks
    for _ in range(2):
        response = s.post("/api/execute", {"userCommand": "whoami"})
        collector.soft_assert_response_code_is(response, expected_code,
                                               f"Request failed: {response.text} {cs.get_server_logs()}")
        collector.soft_assert_response_body_contains(
            response, expected_message, f"{response.text} {cs.get_server_logs()}")

    # ssrf attacks
    for _ in range(2):
        response = s.post(
            "/api/request", {"url": "http://127.0.0.1:8081/health"}, timeout=10)
        collector.soft_assert_response_code_is(response, expected_code,
                                               f"Request failed: {response.text} {cs.get_server_logs()}")
        collector.soft_assert_response_body_contains(
            response, expected_message, f"{response.text} {cs.get_server_logs()}")


def run_test(s: TestServer, c: CoreApi, cs: TestControlServer):
    collector = AssertionCollector()

    cs.check_health()
    cs.uninstall_aikido()
    cs.install_aikido_version("1.4.0")
    cs.start_server()
    s.get("/api/pets/")

    old_start_events = c.get_events("started")
    if not collector.soft_assert(
            len(old_start_events) == 1,
            f"Expected 1 old started event, got {len(old_start_events)}"):
        collector.raise_if_failures()
        return

    send_100_requests(collector)
    send_attacks(collector, 500, "firewall has blocked")

    cs.stop_server()
    cs.install_aikido()
    cs.start_server()
    s.get("/api/pets/")

    current_start_events = c.get_events("started")
    if not collector.soft_assert(
            len(current_start_events) == 1,
            f"Expected 1 current started event, got {len(current_start_events)}"):
        collector.raise_if_failures()
        return

    collector.soft_assert(
        old_start_events[0]["agent"]["version"] != current_start_events[0]["agent"]["version"],
        f"Old version: {old_start_events[0]['agent']['version']} must be different from current version: {current_start_events[0]['agent']['version']}")

    send_100_requests(collector)
    send_attacks(collector, 500, "firewall has blocked")

    cs.stop_server()
    cs.uninstall_aikido()
    cs.start_server()

    send_attacks(collector, 200, "")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c, cs = init_server_and_core()
    run_test(s, c, cs)
