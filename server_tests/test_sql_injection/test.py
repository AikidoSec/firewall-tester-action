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
    start_events = c.get_events("detected_attack")
    response = s.post(
        "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"})
    # assert_response_code_is(response, response_code) # TODO: normalize all apps to return 500
    assert_response_body_contains(response, response_body)

    c.wait_for_new_events(20, old_events_length=len(
        start_events), filter_type="detected_attack")

    all_events = c.get_events("detected_attack")
    new_events = all_events[len(start_events):]

    assert_event_contains_subset_file(new_events[0], expected_json)


def check_sql_injection_payload(payload):
    response = s.post(
        "/api/create", payload)
    if response.status_code == 200:
        pets = s.get("/api/pets/")

        pets_json = pets.json()
        # all the pets must be in Aikido Security
        in_aikido_security = all(
            pet["owner"] == "Aikido Security" for pet in pets_json)
        # write pets_json to a file
        with open("pets.json", "w") as f:
            json.dump(pets_json, f)
        assert in_aikido_security, "All pets must be in Aikido Security, payload: " + \
            str(payload)
    else:
        assert_response_code_is(response, 500, "Payload: " + str(payload))


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
        payload = {
            "name": payload
        }
        check_sql_injection_payload(payload)

    # parameter pollution
    json_payloads = [
        # 1) Simple dup key (last-wins vs first-wins)
        {"name": "hello", "name": "Malicious Pet', 'Gru from the Minions') --"},
        {"name": "Malicious Pet', 'Gru from the Minions') --", "name": "hello"},

        # 2) Duplicates separated by other keys
        {"x": 1, "name": "hello", "y": 2,
            "name": "Malicious Pet', 'Gru from the Minions') --", "z": 3},

        # 3) Type changes across dups (string → bool/number/null/object/array)
        {"name": True, "name": "Malicious Pet', 'Gru from the Minions') --"},
        {"name": 123, "name": "Malicious Pet', 'Gru from the Minions') --"},
        {"name": None, "name": "Malicious Pet', 'Gru from the Minions') --"},
        {"name": {"nested": "obj"}, "name": "Malicious Pet', 'Gru from the Minions') --"},
        {"name": ["a", "b"], "name": "Malicious Pet', 'Gru from the Minions') --"},

        # 4) Case variants (common pollution source if backends normalize)
        {"Name": "hello", "name": "Malicious Pet', 'Gru from the Minions') --"},
        {"NAME": "hello", "name": "Malicious Pet', 'Gru from the Minions') --"},
        {"naMe": "hello", "name": "Malicious Pet', 'Gru from the Minions') --"},

        # 5) Key with trailing/leading spaces (some parsers trim)
        {"name ": "hello", "name": "Malicious Pet', 'Gru from the Minions') --"},
        {" name": "hello", "name": "Malicious Pet', 'Gru from the Minions') --"},

        # 6) Hidden unicode spaces / zero-width chars in key
        # \u200B zero-width space, \u00A0 non-breaking space
        {"na\u200Bme": "hello", "name": "Malicious Pet', 'Gru from the Minions') --"},
        {"na\u00A0me": "hello", "name": "Malicious Pet', 'Gru from the Minions') --"},

        # 7) Homoglyphs (Latin 'a' vs Cyrillic 'а' U+0430)
        {"n\u0430me": "hello", "name": "Malicious Pet', 'Gru from the Minions') --"},

        # 8) Dot/bracket notation keys (some frameworks flatten)
        {"user.name": "hello", "name": "Malicious Pet', 'Gru from the Minions') --"},
        {"user[name]": "hello",
            "name": "Malicious Pet', 'Gru from the Minions') --"},

        # 11) Mixed: one ‘name’ correct, another polluted
        {"primary": {"name": "hello"},
            "name": "Malicious Pet', 'Gru from the Minions') --"},

        # 12) Empty & whitespace values vs polluted
        {"name": "", "name": "Malicious Pet', 'Gru from the Minions') --"},
        {"name": "   ", "name": "Malicious Pet', 'Gru from the Minions') --"},

        # 13) Key normalization collisions (_name, -name)
        {"_name": "hello", "name": "Malicious Pet', 'Gru from the Minions') --"},
        {"-name": "hello", "name": "Malicious Pet', 'Gru from the Minions') --"},

        # 14) Encoded lookalike (name\u005B\u005D)
        {"name[]": "hello", "name": "Malicious Pet', 'Gru from the Minions') --"},

        # 15) Multiple polluted keys to check multi-field logic
        {"name": "Malicious Pet', 'Gru from the Minions') --",
            "title": "Malicious Pet', 'Gru from the Minions') --"},

        # 16) Very long benign preceding value (length tricks)
        {"name": "x"*5000, "name": "Malicious Pet', 'Gru from the Minions') --"},

        # 17) Surrogate pairs / emoji nearby (parser robustness)
        {"name": "hello 😀", "name": "Malicious Pet', 'Gru from the Minions') --"},

        # 18) Key with control chars (some servers strip)
        {"na\rtme": "hello", "name": "Malicious Pet', 'Gru from the Minions') --"},
        {"na\ntme": "hello", "name": "Malicious Pet', 'Gru from the Minions') --"},
    ]

    for payload in json_payloads:
        check_sql_injection_payload(payload)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
