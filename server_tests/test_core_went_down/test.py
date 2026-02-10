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
    response = s.post("/api/execute", {"userCommand": "whoami"})
    collector.soft_assert_response_code_is(response, response_code)

    c.wait_for_new_events(5, old_events_length=len(
        start_events), filter_type="detected_attack")

    all_events = c.get_events("detected_attack")
    new_events = all_events[len(start_events):]

    # Prerequisite: need exactly 1 event to check its contents
    if not collector.soft_assert(len(new_events) == 1, f"Expected 1 new event, got {len(new_events)}"):
        return
    try:
        assert_event_contains_subset_file(new_events[0], expected_json)
    except AssertionError as e:
        collector.add_failure(str(e))


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
