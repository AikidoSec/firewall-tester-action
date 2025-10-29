import requests
import time
import sys
from testlib import *
from core_api import CoreApi
import os
import re


def run_test(s: TestServer, c: CoreApi):

    _ = s.get(
        "/api/pets/", headers={"X-Forwarded-For": "1.3.3.7", "Authorization": "Basic dXNlcjpwYXNzd29yZA=="})

    _ = s.get(
        "/api/pets/", headers={"X-Forwarded-For": "1.3.3.7", "Authorization": "Bearer abcdef1234567890.token.value"})

    _ = s.get(
        "/api/pets/", headers={"X-Forwarded-For": "1.3.3.7", "X-API-Key": "1234567890"})

    _ = s.post(
        "/api/pets/", {"credit_card": "4111111111111111", "cvv": "123", "expiry": "12/26"}, headers={"X-Forwarded-For": "1.3.3.7", "Content-Type": "application/json"})

    _ = s.post(
        "/api/create/", {"name": "Malicious Pet', 'Gru from the Minions') --"}, headers={"X-Forwarded-For": "1.3.3.7", "Content-Type": "application/json"})

    _ = s.post(
        "/api/create/", {"name": "test", "email": "test@test.com", "password": "dXNlcjpwYXNzd29yZA"}, headers={"X-Forwarded-For": "1.3.3.7", "Content-Type": "application/json"})

    _ = s.get(
        "/api/pets/?email=user@example.com&password=secret123", headers={"X-Forwarded-For": "1.3.3.7"})

    _ = s.post("/api/execute", {"userCommand": "`whoami`"},  headers={
        "X-Forwarded-For": "1.3.3.7", "Authorization": "Basic dXNlcjpwYXNzd29yZA=="})

    logs = s.get_logs("test_logs_sensitive_data")
    logs = logs.split("\n")

    for i, line in enumerate(logs, start=1):
        line = line.lower().strip()
        if "aikido" not in line and "zen" not in line:
            continue
        assert_line_contains_sensitive_data(line, i)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
