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


def f(config_file: str):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), config_file)


def check_shell_injection(response_code, response_body, event_id, expected_json):
    start_events = c.get_events()
    response = s.post("/shell_injection", {"command": "`whoami`"})
    assert_response_code_is(response, response_code)
    assert_response_body_contains(response, response_body)

    c.wait_for_new_events(5, old_events_length=len(start_events))

    all_events = c.get_events()
    new_events = all_events[len(start_events):]

#    assert_events_length_is_at_least(new_events, event_id + 1)
    assert_started_event_is_valid(all_events[0])
    assert_event_contains_subset_file(new_events[0], expected_json)


def run_test(s: TestServer, c: CoreApi):
    check_shell_injection(500, "", 1, f("expect_detection_blocked.json"))

    c.update_runtime_config_file(f("change_config_disable_blocking.json"))
    check_shell_injection(200, "Shell executed!", 2,
                          f("expect_detection_not_blocked.json"))

    c.update_runtime_config_file(f("start_config.json"))
    check_shell_injection(500, "", 3, f("expect_detection_blocked.json"))


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
