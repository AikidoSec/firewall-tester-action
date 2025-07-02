import requests
import time
import sys
from testlib import *
from core_api import CoreApi
import os


def f(config_file: str):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), config_file)


def run_test(s: TestServer, c: CoreApi):
    # curl -H "Authorization: Basic dXNlcjpwYXNzd29yZA==" https://example.com/api/login

    # Basic Auth Header
    response = s.get(
        "/api/pets/", headers={"X-Forwarded-For": "1.3.3.7", "Authorization": "Basic dXNlcjpwYXNzd29yZA=="})

    # Bearer Token curl -H "Authorization: Bearer abcdef1234567890.token.value" https://example.com/api/data
    response = s.get(
        "/api/pets/", headers={"X-Forwarded-For": "1.3.3.7", "Authorization": "Bearer abcdef1234567890.token.value"})

    # API Key in Header curl -H "x-api-key: my_api_key_123456" https://example.com/api/secure
    response = s.get(
        "/api/pets/", headers={"X-Forwarded-For": "1.3.3.7", "X-API-Key": "1234567890"})

    # Credit Card in Payload curl -X POST https://example.com/api/pay -H "Content-Type: application/json" -d '{"credit_card":"4111111111111111","cvv":"123","expiry":"12/26"}'
    response = s.post(
        "/api/pets/", {"credit_card": "4111111111111111", "cvv": "123", "expiry": "12/26"}, headers={"X-Forwarded-For": "1.3.3.7", "Content-Type": "application/json"})

    # Name in Payload curl -X POST https://example.com/api/create -H "Content-Type: application/json" -d '{"name":"John Doe"}'
    response = s.post(
        "/api/create/", {"name": "Malicious Pet', 'Gru from the Minions') --"}, headers={"X-Forwarded-For": "1.3.3.7", "Content-Type": "application/json"})

    # Email and Password in Query curl "https://example.com/api/login?email=user@example.com&password=secret123"
    response = s.get(
        "/api/pets/?email=user@example.com&password=secret123", headers={"X-Forwarded-For": "1.3.3.7"})

    # Shell Injection curl -X POST https://example.com/api/execute -d '{"userCommand":"`whoami`"}'
    response = s.post("/api/execute", {"userCommand": "`whoami`"},  headers={
                      "X-Forwarded-For": "1.3.3.7", "Authorization": "Basic dXNlcjpwYXNzd29yZA=="})

    logs = s.get_logs("test_logs_sensitive_data")
    # save logs to file

    with open("logs.txt", "w") as f:
        f.write(logs)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
