from testlib import *
from core_api import CoreApi


def check_attacks_blocked(response_code):

    # sql injection
    response = s.post(
        "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"})
    assert_response_code_is(response, response_code, "sql injection")

    # shell injection
    response = s.post("/api/execute", {"userCommand": "whoami"})
    assert_response_code_is(response, response_code, "shell injection")

    # path traversal
    response = s.get("/api/read?path=../secrets/key.txt")
    assert_response_code_is(response, response_code, "path traversal")


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


def run_test(s: TestServer, c: CoreApi):
    check_attacks_blocked(500)

    c.set_mock_server_down()
    time.sleep(70)

    check_attacks_blocked(500)

    for _ in range(5):
        response = s.get("/test_ratelimiting_1")
        assert_response_code_is(response, 200, response.text)

    time.sleep(10)

    for i in range(10):
        response = s.get("/test_ratelimiting_1")
        if i < 5:
            pass
        else:
            assert_response_code_is(response, 429, response.text)

    c.set_mock_server_up()

    check_event_is_submitted_shell_injection(
        500, "expect_detection_blocked.json")

    c.set_mock_server_timeout()

    time.sleep(70)

    check_attacks_blocked(500)

    c.set_mock_server_up()

    check_event_is_submitted_shell_injection(
        500, "expect_detection_blocked.json")


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
