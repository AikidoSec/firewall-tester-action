from testlib import *
from core_api import CoreApi


def check_attacks_blocked(collector, s, response_code):

    # sql injection
    response = s.post(
        "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"})
    collector.soft_assert_response_code_is(
        response, response_code, "sql injection")

    # shell injection
    response = s.post("/api/execute", {"userCommand": "whoami"})
    collector.soft_assert_response_code_is(
        response, response_code, "shell injection")

    # path traversal
    response = s.get("/api/read?path=../secrets/key.txt")
    collector.soft_assert_response_code_is(
        response, response_code, "path traversal")


def check_event_is_submitted_shell_injection(collector, s, c, response_code, expected_json):
    start_events = c.get_events("detected_attack")
    request_started_at_ms = int(time.time() * 1000) - 1000
    response = s.post("/api/execute", {"userCommand": "whoami"})
    collector.soft_assert_response_code_is(response, response_code)

    deadline = time.monotonic() + 5
    new_events = []
    candidate_events = []
    last_error = None

    while time.monotonic() < deadline:
        all_events = c.get_events("detected_attack")
        new_events = all_events[len(start_events):]
        candidate_events = [
            event for event in new_events
            if event.get("time", request_started_at_ms) >= request_started_at_ms
        ]

        for event in candidate_events:
            try:
                assert_event_contains_subset_file(event, expected_json)
                return
            except AssertionError as e:
                last_error = e

        time.sleep(1)

    collector.add_failure(
        f"Expected at least one new event matching '{expected_json}', "
        f"got {len(new_events)} new events and "
        f"{len(candidate_events)} after this request. "
        f"Last mismatch: {last_error}"
    )


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    check_attacks_blocked(collector, s, 500)

    c.set_mock_server_down()
    time.sleep(70)

    check_attacks_blocked(collector, s, 500)

    for _ in range(5):
        response = s.get("/test_ratelimiting_1")
        collector.soft_assert_response_code_is(response, 200, response.text)

    time.sleep(5)

    for i in range(10):
        response = s.get("/test_ratelimiting_1")
        if i < 5:
            pass
        else:
            collector.soft_assert_response_code_is(
                response, 429, response.text)

    c.set_mock_server_up()

    check_event_is_submitted_shell_injection(
        collector, s, c, 500, "expect_detection_blocked.json")

    c.set_mock_server_timeout()

    time.sleep(70)

    check_attacks_blocked(collector, s, 500)

    c.set_mock_server_up()
    time.sleep(30)

    check_event_is_submitted_shell_injection(
        collector, s, c, 500, "expect_detection_blocked.json")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
