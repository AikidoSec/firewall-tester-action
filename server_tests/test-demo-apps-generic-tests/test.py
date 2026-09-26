
import json
from testlib import *
from core_api import CoreApi
import os
import base64

'''
1. Check for user blocking.
2. Check for bot blocking.
3. Send a very big request to the server.
4. Send an sql injection payload to see if the server it's still working.
'''


def build_nested_json_text(depth: int):
    result = '{"a":"b"}'
    for level in range(1, depth + 1):
        result = '{"key' + str(level) + '":' + result + '}'
    return result


def create_token(json_data):
    if isinstance(json_data, str):
        payload = json_data
    else:
        payload = json.dumps(json_data)
    return f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{base64.b64encode(payload.encode()).decode()}.1234567890"


def check_pets_after_attack(collector, s, response, description):
    if not collector.soft_assert(get_response_status_code(response) is not None,
                                 f"No HTTP response for {description}"):
        return
    pets = s.get("/api/pets/")
    if collector.soft_assert_response_code_is(pets, 200, f"Reading pets after {description}"):
        collector.soft_assert('Gru' not in pets.text, f"Bypass for {description}")


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    # ------ user blocking ------

    response = s.get_raw("/api/pets/", headers={
        "user": "123456"})
    response.read()
    collector.soft_assert_response_code_is(
        response, 200, "Expected 200 for user 123456")

    response = s.get_raw("/api/pets/", headers={
        "user": "789"})
    response.read()
    collector.soft_assert_response_code_is(
        response, 403, "Expected 403 for user 789")

    # ------ Bot blocking ------

    response = s.get("/api/pets/", headers={
        "User-Agent": "1234googlebot1234"})
    collector.soft_assert_response_code_is(
        response, 403)

    # ------ Big request ------
    file_path = os.path.join(os.path.dirname(__file__), "test.json")
    with open(file_path, 'r', encoding="utf-8") as file:
        response = s.post("/api/create", json.load(file))
    collector.soft_assert_response_code_is(
        response, 200, "Expected 200 for /api/create")

    response = s.post(
        "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"})
    collector.soft_assert_response_code_is(
        response, 500, "Expected 500 for /api/create")

    # ------ Big Nested JSON ------
    body = '{"a":' + build_nested_json_text(8000) + ',"name":' + json.dumps(
        "Malicious Pet', 'Gru from the Minions') --") + '}'
    response = s.post_raw("/api/create", data=body, headers={"Content-Type": "application/json"})
    check_pets_after_attack(collector, s, response, "big nested json")

    # ------ Big Nested JSON in token ------
    token = create_token(build_nested_json_text(8000))
    body = {
        "a": token,
        "name": "Malicious Pet', 'Gru from the Minions') --"
    }
    response = s.post("/api/create", data=body)
    check_pets_after_attack(collector, s, response, "big nested json in token")

    # ------ Token in token ------
    token = create_token({"a": "b"})
    for _ in range(10):
        token = create_token({"a": token})
    body = {
        "a": token,
        "name": "Malicious Pet', 'Gru from the Minions') --"
    }
    response = s.post("/api/create", data=body)
    check_pets_after_attack(collector, s, response, "token in token")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
