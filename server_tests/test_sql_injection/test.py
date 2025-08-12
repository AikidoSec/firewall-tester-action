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
4. Checks that the payload is blocked.
5. Send more requests to the app, and check that the payload is blocked.
'''


def check_sql_injection(response_code, response_body, event_id, expected_json):
    start_events = c.get_events()
    response = s.post(
        "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"})
    # assert_response_code_is(response, response_code) # TODO: normalize all apps to return 500
    assert_response_body_contains(response, response_body)

    c.wait_for_new_events(20, old_events_length=len(start_events))

    all_events = c.get_events()
    new_events = all_events[len(start_events):]

    # assert_events_length_is(new_events, 1)
    assert_started_event_is_valid(all_events[0])
    assert_event_contains_subset_file(new_events[0], expected_json)


def check_sql_injection_payload(payload):
    response = s.post(
        "/api/create", {"name": payload})
    if response.status_code == 200:
        pets = s.get("/api/pets/")

        pets_json = pets.json()
        # all the pets must be in Aikido Security
        in_aikido_security = all(
            pet["owner"] == "Aikido Security" for pet in pets_json)
        # write pets_json to a file
        with open("pets.json", "w") as f:
            json.dump(pets_json, f)
        assert in_aikido_security, "All pets must be in Aikido Security, payload: " + payload
    else:
        assert_response_code_is(response, 500, "Payload: " + payload)


def check_sql_injection_select(payload):
    response = s.get(f"/api/pets/{payload}")
    assert_response_code_is_not(response, 200, "Payload: " + payload)


def run_test(s: TestServer, c: CoreApi):
    check_sql_injection(500, "", 1, "expect_detection_blocked.json")

    c.update_runtime_config_file("change_config_disable_blocking.json")
    check_sql_injection(200, "", 2,
                        "expect_detection_not_blocked.json")

    c.update_runtime_config_file("start_config.json")
    check_sql_injection(500, "", 3, "expect_detection_blocked.json")
    s.get("/clear")
    payloads = [
        "Malicious Pet', 'Gru from the Minions') --",
        "\0Malicious Pet', 'Gru from the Minions') --",
        "%00Malicious Pet', 'Gru from the Minions') --",
        "\x00Malicious Pet', 'Gru from the Minions') --",

        "Malicious Pet\0', 'Gru from the Minions') --",
        "Malicious Pet%00', 'Gru from the Minions') --",
        "Malicious Pet\x00', 'Gru from the Minions') --",

        "Malicious Pet‘, ‘Gru from the Minions‘) --",
        "Malicious Pet‘， ‘Gru from the Minions‘) --",
        "Malicious Pet‘‚ ‘Gru from the Minions‘) --",

        "Malicious Pet＇, ‘Gru from the Minions＇) --",
        "Malicious Pet＇， ‘Gru from the Minions＇) --",
        "Malicious Pet＇‚ ‘Gru from the Minions＇) --",


        "Malicious Pet’, ’Gru from the Minions’) --",
        "Malicious Pet’， ’Gru from the Minions’) --",
        "Malicious Pet’‚ ’Gru from the Minions’) --",

    ]
    for payload in payloads:
        check_sql_injection_payload(payload)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
