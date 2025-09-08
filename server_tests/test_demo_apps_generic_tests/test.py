
import json
from testlib import *
from core_api import CoreApi
import os
import base64
import sys
sys.setrecursionlimit(40001)

'''
1. Check for user blocking.
2. Check for bot blocking.
3. Send a very big request to the server.
4. Send an sql injection payload to see if the server it's still working.
'''


def build_nested_dict(depth: int, json_data: dict = {}):
    if depth == 0:
        return {"a": "b"}
    json_data[f"key{depth}"] = build_nested_dict(depth - 1,  {})
    return json_data


def create_token(json_data: dict):
    return f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{base64.b64encode(json.dumps(json_data).encode()).decode()}.1234567890"


def run_test(s: TestServer, c: CoreApi):
    # ------ user blocking ------

    response = s.get_raw("/api/pets/", headers={
        "user": "123456"})
    assert_response_code_is(
        response, 200, f"Expected 200 for user 123456 {response.read()}")

    response = s.get_raw("/api/pets/", headers={
        "user": "789"})
    assert_response_code_is(
        response, 403, f"Expected 403 for user 789 {response.read()}")

    # ------ Bot blocking ------

    response = s.get("/api/pets/", headers={
        "User-Agent": "1234googlebot1234"})
    assert_response_code_is(
        response, 403, f"Expected 403 for  {response.text}")

    # ------ Big request ------
    file_path = os.path.join(os.path.dirname(__file__), "test.json")
    response = s.post("/api/create", json.load(open(file_path, 'r')))
    assert_response_code_is(
        response, 200, f"Expected 200 for /api/create {response.text}")

    response = s.post(
        "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"})
    assert_response_code_is(
        response, 500, f"Expected 500 for /api/create {response.text}")

    # ------ Big Nested JSON ------
    json_data = build_nested_dict(8000)
    body = {
        "a": json_data,
        "name": "Malicious Pet', 'Gru from the Minions') --"
    }
    response = s.post("/api/create", data=body)
    pets = s.get("/api/pets/")
    assert 'Gru' not in pets.text, f"Bypass for big nested json, pets: {pets.text}"

    # ------ Big Nested JSON in token ------
    token = create_token(json_data)
    body = {
        "a": token,
        "name": "Malicious Pet', 'Gru from the Minions') --"
    }
    response = s.post("/api/create", data=body)
    pets = s.get("/api/pets/")
    assert 'Gru' not in pets.text, f"Bypass for big nested json in token, pets: {pets.text}"

    # ------ Token in token ------
    token = create_token({"a": "b"})
    for _ in range(10):
        token = create_token({"a": token})
    body = {
        "a": token,
        "name": "Malicious Pet', 'Gru from the Minions') --"
    }
    response = s.post("/api/create", data=body)
    pets = s.get("/api/pets/")
    assert 'Gru' not in pets.text, f"Bypass for token in token, pets: {pets.text}"


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
