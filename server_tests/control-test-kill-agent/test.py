
from testlib import *
from core_api import CoreApi

"""
1. Check control server is running, start the server and send 100 requests and 8 attacks
2. Kill the agent and send 100 requests and 8 attacks (attacks should be blocked)
3. Restart the server using stop start send an attack and check event is submitted to core
4. Kill the agent and send 100 requests and 8 attacks (attacks should be blocked)
5. Graceful restart the server, send an attack and check event is submitted to core
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


def restart_server_using_stop_start(sleep_time: int = 0):
    cs.stop_server()
    cs.status_is_running(False)
    time.sleep(sleep_time)
    cs.start_server()
    cs.status_is_running(True)


def run_test(s: TestServer, c: CoreApi, cs: TestControlServer):
    collector = AssertionCollector()

    cs.check_health()
    cs.start_server()

    send_100_requests(collector)
    send_attacks(collector)

    cs.kill_agent()

    send_100_requests(collector)
    send_attacks(collector)

    restart_server_using_stop_start()
    s.get("/api/pets/")

    check_event_is_submitted_shell_injection(
        collector, 500, "expect_detection_blocked.json")

    cs.kill_agent()
    send_100_requests(collector)
    send_attacks(collector)

    cs.graceful_restart()
    cs.status_is_running(True)
    s.get("/api/pets/")

    check_event_is_submitted_shell_injection(
        collector, 500, "expect_detection_blocked.json")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c, cs = init_server_and_core()
    run_test(s, c, cs)
