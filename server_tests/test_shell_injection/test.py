import requests
import time
import sys
from testlib import *
from core_api import CoreApi
import os


'''
1. Sets up a simple config and env AIKIDO_BLOCK=1.
2. Sends an attack request to a route, that will cause sending a detection event.
3. Checks that the detection event was submitted and is valid.
'''


def check_shell_injection(response_code, expected_json):
    start_events = c.get_events()
    response = s.post("/api/execute", {"userCommand": "whoami"})
    assert_response_code_is(response, response_code)

    c.wait_for_new_events(5, old_events_length=len(start_events))

    all_events = c.get_events()
    new_events = all_events[len(start_events):]
    with open("new_events.json", "w") as f:
        json.dump(new_events, f)
   # assert_events_length_is(new_events, 1)
    assert_started_event_is_valid(all_events[0])
    assert_event_contains_subset_file(new_events[0], expected_json)


def run_test(s: TestServer, c: CoreApi):
    check_shell_injection(500, "expect_detection_blocked.json")

    c.update_runtime_config_file("change_config_disable_blocking.json")
    check_shell_injection(200, "expect_detection_not_blocked.json")

    c.update_runtime_config_file("start_config.json")
    check_shell_injection(500, "expect_detection_blocked.json")


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
