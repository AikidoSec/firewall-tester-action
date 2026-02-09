
from testlib import *
from core_api import CoreApi


"""
1. Check control server is running, start the server and send 100 requests and 8 attacks
2. Restart the server using restart and send 8 attacks and 100 requests
3. Restart the server using restart, send one attack, and check event is submitted to core
4. Stop server and start it again using restart and check it's working fine
"""


def send_100_requests(collector):
    for _ in range(100):
        response = s.get("/api/pets/")
        collector.soft_assert_response_code_is(response, 200,
                                               f"Request failed: {response.text} {cs.get_server_logs()}")


def send_attacks(collector):
    # path traversal attacks
    for _ in range(2):
        response = s.get("/api/read?path=../secrets/key.txt")
        collector.soft_assert_response_code_is(response, 500,
                                               f"Request failed: {response.text} {cs.get_server_logs()}")
        collector.soft_assert_response_body_contains(
            response, "firewall has blocked a path traversal", f"{response.text} {cs.get_server_logs()}")

    # sql injection attacks
    for _ in range(2):
        response = s.post(
            "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"})
        collector.soft_assert_response_code_is(response, 500,
                                               f"Request failed: {response.text} {cs.get_server_logs()}")
        collector.soft_assert_response_body_contains(
            response, "firewall has blocked an SQL injection", f"{response.text} {cs.get_server_logs()}")

    # shell injection attacks
    for _ in range(2):
        response = s.post("/api/execute", {"userCommand": "whoami"})
        collector.soft_assert_response_code_is(response, 500,
                                               f"Request failed: {response.text} {cs.get_server_logs()}")
        collector.soft_assert_response_body_contains(
            response, "firewall has blocked a shell injection", f"{response.text} {cs.get_server_logs()}")

    # ssrf attacks
    for _ in range(2):
        response = s.post(
            "/api/request", {"url": "http://127.0.0.1:8081"}, timeout=10)
        collector.soft_assert_response_code_is(response, 500,
                                               f"Request failed: {response.text} {cs.get_server_logs()}")
        collector.soft_assert_response_body_contains(
            response, "firewall has blocked a server-side request forgery", f"{response.text} {cs.get_server_logs()}")


def check_event_is_submitted_shell_injection(collector, response_code, expected_json):
    start_events = c.get_events("detected_attack")
    response = s.post("/api/execute", {"userCommand": "whoami"})
    collector.soft_assert_response_code_is(response, response_code)

    c.wait_for_new_events(10, old_events_length=len(
        start_events), filter_type="detected_attack")

    all_events = c.get_events("detected_attack")
    new_events = all_events[len(start_events):]

    if not collector.soft_assert(
            len(new_events) == 1,
            f"Expected 1 detected_attack event, got {len(new_events)}"):
        return

    try:
        assert_event_contains_subset_file(new_events[0], expected_json)
    except AssertionError as e:
        collector.add_failure(str(e))


def run_test(s: TestServer, c: CoreApi, cs: TestControlServer):
    collector = AssertionCollector()

    cs.check_health()
    cs.start_server()

    send_100_requests(collector)
    send_attacks(collector)

    cs.restart()
    cs.status_is_running(True)

    send_attacks(collector)
    send_100_requests(collector)

    cs.restart()
    cs.status_is_running(True)
    time.sleep(5)
    s.get("/api/pets/")

    check_event_is_submitted_shell_injection(
        collector, 500, "expect_detection_blocked.json")

    # stop server and start it again usng graceful restart
    cs.stop_server()
    cs.status_is_running(False)
    cs.restart()
    cs.status_is_running(True)
    time.sleep(5)
    s.get("/api/pets/")

    check_event_is_submitted_shell_injection(
        collector, 500, "expect_detection_blocked.json")
    send_attacks(collector)
    send_100_requests(collector)

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c, cs = init_server_and_core()
    run_test(s, c, cs)
