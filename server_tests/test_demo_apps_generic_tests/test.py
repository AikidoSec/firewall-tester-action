
from testlib import *
from core_api import CoreApi
import os


'''
1. Send a very big request to the server.
2. Send an sql injection payload to see if the server it's still working.
3. Check for bot blocking.
4. Check for user blocking.
'''


def run_test(s: TestServer, c: CoreApi):
    file_path = os.path.join(os.path.dirname(__file__), "test.json")
    response = s.post("/api/create", json.load(open(file_path, 'r')))
    assert_response_code_is(
        response, 200, f"Expected 200 for /api/create {response.text}")

    response = s.post(
        "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"})
    assert_response_code_is(
        response, 500, f"Expected 500 for /api/create {response.text}")

    # ------ Bot blocking ------

    response = s.get("/api/pets/", headers={
        "User-Agent": "1234googlebot1234"})
    assert_response_code_is(
        response, 403, f"Expected 403 for / {response.text}")

    # ------ user blocking ------

    response = s.get("/api/pets/", headers={
        "user": "123456"})
    assert_response_code_is(
        response, 200, f"Expected 200 for user 123456 {response.text}")

    response = s.get("/api/pets/", headers={
        "user": "789"})
    assert_response_code_is(
        response, 403, f"Expected 403 for user 789 {response.text}")


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
