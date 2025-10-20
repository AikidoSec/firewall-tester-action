
from testlib import *
from core_api import CoreApi

"""
1. Check control server is running, start the server and send 100 requests and 100 attacks
2. Restart the server using graceful restart and send 100 attacks and 100 requests
3. Restart the server using graceful restart, send one attack, and check event is submitted to core
4. Stop server and start it again using graceful restart and check it's working fine
"""


def send_100_requests():
    for _ in range(100):
        response = s.get("/api/pets/")
        assert_response_code_is(response, 200,
                                f"Request failed: {response.text} {cs.get_server_logs()}")


def send_100_attacks():
    # path traversal attacks
    for _ in range(25):
        response = s.get("/api/read?path=../secrets/key.txt")
        assert_response_code_is(response, 500,
                                f"Request failed: {response.text} {cs.get_server_logs()}")
        assert_response_body_contains(
            response, "firewall has blocked a path traversal", f"{response.text} {cs.get_server_logs()}")

    # sql injection attacks
    for _ in range(25):
        response = s.post(
            "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"})
        assert_response_code_is(response, 500,
                                f"Request failed: {response.text} {cs.get_server_logs()}")
        assert_response_body_contains(
            response, "firewall has blocked an SQL injection", f"{response.text} {cs.get_server_logs()}")

    # shell injection attacks
    for _ in range(25):
        response = s.post("/api/execute", {"userCommand": "whoami"})
        assert_response_code_is(response, 500,
                                f"Request failed: {response.text} {cs.get_server_logs()}")
        assert_response_body_contains(
            response, "firewall has blocked a shell injection", f"{response.text} {cs.get_server_logs()}")

    # ssrf attacks
    for _ in range(25):
        response = s.post(
            "/api/request", {"url": "http://127.0.0.1:8081"}, timeout=10)
        assert_response_code_is(response, 500,
                                f"Request failed: {response.text} {cs.get_server_logs()}")
        assert_response_body_contains(
            response, "firewall has blocked a server-side request forgery", f"{response.text} {cs.get_server_logs()}")


def check_event_is_submitted_shell_injection(response_code, expected_json):
    start_events = c.get_events("detected_attack")
    response = s.post("/api/execute", {"userCommand": "whoami"})
    assert_response_code_is(response, response_code)

    c.wait_for_new_events(5, old_events_length=len(
        start_events), filter_type="detected_attack")

    all_events = c.get_events("detected_attack")
    new_events = all_events[len(start_events):]

    assert_events_length_is(new_events, 1)
    assert_event_contains_subset_file(new_events[0], expected_json)


def run_test(s: TestServer, c: CoreApi, cs: TestControlServer):
    cs.check_health()
    cs.start_server()

    send_100_requests()
    send_100_attacks()

    cs.graceful_restart()
    cs.status_is_running(True)

    send_100_attacks()
    send_100_requests()

    cs.graceful_restart()
    cs.status_is_running(True)
    time.sleep(60 * 2)

    check_event_is_submitted_shell_injection(
        500, "expect_detection_blocked.json")

    # stop server and start it again usng graceful restart
    cs.stop_server()
    cs.status_is_running(False)
    cs.graceful_restart()
    cs.status_is_running(True)
    time.sleep(60 * 2)
    check_event_is_submitted_shell_injection(
        500, "expect_detection_blocked.json")
    send_100_attacks()
    send_100_requests()


if __name__ == "__main__":
    args, s, c, cs = init_server_and_core()
    run_test(s, c, cs)
