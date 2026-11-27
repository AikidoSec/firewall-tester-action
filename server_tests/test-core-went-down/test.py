from testlib import *
from core_api import CoreApi


def check_attacks_blocked(collector, s, response_code, *, phase):

    # sql injection
    response = s.post(
        "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"})
    collector.soft_assert_response_code_is(
        response, response_code, f"SQL injection should still be blocked {phase}")

    # shell injection
    response = s.post("/api/execute", {"userCommand": "whoami"})
    collector.soft_assert_response_code_is(
        response, response_code, f"Shell injection should still be blocked {phase}")

    # path traversal
    response = s.get("/api/read?path=../secrets/key.txt")
    collector.soft_assert_response_code_is(
        response, response_code, f"Path traversal should still be blocked {phase}")


def check_event_is_submitted_shell_injection(
        collector, s, c, response_code, expected_json, max_wait_time=5, *, phase):
    start_events = c.get_events("detected_attack")
    request_started_at_ms = int(time.time() * 1000) - 1000
    response = s.post("/api/execute", {"userCommand": "whoami"})
    collector.soft_assert_response_code_is(
        response, response_code, f"Shell injection should still be blocked {phase}"
    )

    deadline = time.monotonic() + max_wait_time
    new_events = []
    candidate_events = []
    last_error = None

    while True:
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

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(1, remaining))

    collector.add_failure(
        f"Expected at least one new event matching '{expected_json}', "
        f"got {len(new_events)} new events and "
        f"{len(candidate_events)} after this request. "
        f"Last mismatch: {last_error}"
    )


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    check_attacks_blocked(collector, s, 500, phase="before core goes offline")

    c.set_mock_server_down()
    time.sleep(70)

    check_attacks_blocked(collector, s, 500, phase="while core is offline")

    for i in range(5):
        response = s.get("/test_ratelimiting_1")
        collector.soft_assert_response_code_is(
            response, 200,
            f"GET /test_ratelimiting_1 request {i + 1} is within the cached limit while core is down",
        )

    time.sleep(5)

    for i in range(10):
        response = s.get("/test_ratelimiting_1")
        if i < 5:
            pass
        else:
            collector.soft_assert_response_code_is(
                response, 429,
                f"GET /test_ratelimiting_1 request {i + 6} exceeds the cached limit while core is down",
            )

    c.set_mock_server_up()

    check_event_is_submitted_shell_injection(
        collector, s, c, 500, "expect_detection_blocked.json", phase="after core comes back online")

    c.set_mock_server_timeout()

    time.sleep(70)

    check_attacks_blocked(collector, s, 500, phase="while core times out")

    c.set_mock_server_up()

    check_event_is_submitted_shell_injection(
        collector, s, c, 500, "expect_detection_blocked.json", max_wait_time=70,
        phase="after core recovers from a timeout")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
