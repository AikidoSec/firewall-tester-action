import datetime
import time
import requests
import argparse
from core_api import CoreApi
import json
import subprocess
import random
import string
import inspect
import os
import http.client
import re


def localhost_get_request(port, route="", headers={}, benchmark=False, raw=False):
    global benchmarks, s

    start_time = datetime.datetime.now()

    for attempt in range(3):
        try:
            if raw:
                conn = http.client.HTTPConnection("localhost", port)
                conn.request("GET", route, headers=headers)
                r = conn.getresponse()
            else:
                r = requests.get(
                    f"http://localhost:{port}{route}", headers=headers)
            break  # Success, exit retry loop
        except Exception as e:
            print(f"Error (attempt {attempt + 1}/3): {e}")
            if attempt == 2:  # Last attempt
                return None
            time.sleep(0.1)  # Brief delay before retry

    end_time = datetime.datetime.now()
    delta = end_time - start_time
    elapsed_ms = delta.total_seconds() * 1000

    if benchmark:
        benchmarks.append(elapsed_ms)

    time.sleep(0.001)
    return r


def localhost_post_request(port, route, data, headers={}, benchmark=False, timeout=100):
    global benchmarks, s

    start_time = datetime.datetime.now()

    for attempt in range(3):
        try:
            r = requests.post(f"http://localhost:{port}{route}",
                              json=data, headers=headers, timeout=timeout)
            break  # Success, exit retry loop
        except Exception as e:
            print(f"Error (attempt {attempt + 1}/3): {e}")
            if attempt == 2:  # Last attempt
                return requests.Response()
            time.sleep(0.1)  # Brief delay before retry

    if benchmark:
        benchmarks.append(elapsed_ms)

    time.sleep(0.001)
    return r


def localhost_request_request(port, method, route, data, headers, benchmark, timeout):
    return requests.request(method, f"http://localhost:{port}{route}", json=data, headers=headers, timeout=timeout)


def init_server_and_core():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test_name", type=str, required=True)
    parser.add_argument("--server_port", type=int, required=True)
    parser.add_argument("--control_server_port", type=int, required=False)
    parser.add_argument("--token", type=str, required=True)
    parser.add_argument("--core_port", type=int, default=3000)
    parser.add_argument("--config_update_delay", type=int, default=60)
    args = parser.parse_args()

    server = TestServer(port=args.server_port, token=args.token)
    core = CoreApi(token=args.token, core_url=f"http://localhost:{args.core_port}", test_name=args.test_name,
                   config_update_delay=args.config_update_delay)
    if args.control_server_port:
        control_server = TestControlServer(port=args.control_server_port)
        return args, server, core, control_server
    else:
        return args, server, core


"""
- `GET /health` - Health check
- `GET /status` - Get Apache status
- `POST /start_server` - Start Apache
- `POST /stop_server` - Stop Apache
- `POST /restart` - Hard restart Apache
- `POST /graceful-restart` - Graceful restart Apache
- `POST /graceful-stop` - Graceful stop Apache
- `GET /get-server-logs` - Get Apache logs
- `GET /config-test` - Test Apache configuration
"""


class TestControlServer:
    def __init__(self, port: int):
        self.port = port

    def check_health(self):
        for i in range(3):
            r = localhost_get_request(self.port, "/health")
            if r and r.status_code == 200:
                break
            time.sleep(i * 3)
        assert_response_code_is(
            r, 200, f"Health check failed: {r.text if r else 'No response'}")
        assert_response_body_contains(
            r, "\"status\":\"healthy\"", f"Health check failed: {r.text}")

    def status_is_running(self, running: bool):
        r = localhost_get_request(self.port, "/status")
        assert_response_code_is(r, 200, f"Status check failed: {r.text}")
        if running:
            assert_response_body_contains(
                r, "running", f"Server is not running {r.text}")
        else:
            assert_response_body_contains(
                r, "stopped", f"Server is not stopped {r.text}")

    def start_server(self):
        r = localhost_post_request(self.port, "/start_server", {})
        assert_response_code_is(r, 200, f"Start server failed: {r.text}")
        assert_response_body_contains(
            r, "\"is_running\":true", f"Server is not running {r.text}")
        time.sleep(3)

    def stop_server(self):
        r = localhost_post_request(self.port, "/stop_server", {})
        assert_response_code_is(r, 200, f"Stop server failed: {r.text}")
        assert_response_body_contains(
            r, "\"is_running\":false", f"Server is not stopped {r.text}")

    def restart(self):
        r = localhost_post_request(self.port, "/restart", {})
        assert_response_code_is(r, 200, f"Restart failed: {r.text}")
        assert_response_body_contains(
            r, "\"is_running\":true", f"Server is not running {r.text}")

    def graceful_restart(self):
        r = localhost_post_request(self.port, "/graceful-restart", {})
        assert_response_code_is(r, 200, f"Graceful restart failed: {r.text}")
        assert_response_body_contains(
            r, "\"is_running\":true", f"Server is not running {r.text}")
        time.sleep(3)

    def graceful_stop_server(self):
        r = localhost_post_request(self.port, "/graceful-stop", {})
        assert_response_code_is(r, 200, f"Graceful stop failed: {r.text}")
        time.sleep(3)

    def get_server_logs(self, type="error", lines=50):
        response = localhost_get_request(
            self.port, f"/get-server-logs?type={type}&lines={lines}")
        return response.text if response else None

    def uninstall_aikido(self):
        r = localhost_post_request(self.port, "/uninstall-aikido", {})
        assert_response_code_is(r, 200, f"Uninstall aikido failed: {r.text}")
        assert_response_body_contains(
            r, "\"status\":\"success\"", f"Uninstall aikido failed: {r.text}")

    def install_aikido(self):
        r = localhost_post_request(self.port, "/install-aikido", {})
        assert_response_code_is(r, 200, f"Install aikido failed: {r.text}")
        assert_response_body_contains(
            r, "\"status\":\"success\"", f"Install aikido failed: {r.text}")

    def install_aikido_version(self, version: str):
        r = localhost_post_request(
            self.port, "/install-aikido-version", {"version": version})
        assert_response_code_is(
            r, 200, f"Install aikido version failed: {r.text}")
        assert_response_body_contains(
            r, "\"status\":\"success\"", f"Install aikido version failed: {r.text}")

    def config_test(self):
        return localhost_get_request(self.port, "/config-test")


class TestServer:
    def __init__(self, port: int, token: str):
        self.port = port
        self.token = token

    def get(self, route="", headers={}, benchmark=False):
        return localhost_get_request(self.port, route, headers, benchmark)

    def get_raw(self, route="", headers={}, benchmark=False):
        return localhost_get_request(self.port, route, headers, benchmark, raw=True)

    def post(self, route="", data={}, headers={}, benchmark=False, timeout=100):
        return localhost_post_request(self.port, route, data, headers, benchmark, timeout)

    def request(self, method, route="", data={}, headers={}, benchmark=False, timeout=100):
        return localhost_request_request(self.port, method, route, data, headers, benchmark, timeout)

    def get_logs(self, container_name: str):
        # this gets the logs from the server (docker logs <container_name>)
        logs = subprocess.check_output(
            ["docker", "logs", container_name], stderr=subprocess.STDOUT)
        return logs.decode("utf-8")


def assert_event_contains_subset(event, event_subset, dry_mode=False):
    """
    Recursively checks that all keys and values in the subset JSON exist in the event JSON
    and have the same values. If a key in the subset is a list, all its elements must exist in the
    corresponding list in the event.

    :param event: The event JSON dictionary
    :param subset: The subset JSON dictionary
    :raises AssertionError: If the subset is not fully contained within the event
    """
    def result(assertion_error):
        if dry_mode:
            return False
        raise assertion_error

    print(f"Searching {event_subset} in {event} (dry_mode = {dry_mode})...")

    if event is None:
        print(f"Event is None!")
        return False

    if isinstance(event_subset, dict):
        found_all_keys = True
        for key, value in event_subset.items():
            if key not in event:
                return result(AssertionError(f"Key '{key}' not found in '{event}'."))
            if not assert_event_contains_subset(event[key], value, dry_mode):
                found_all_keys = False
        return found_all_keys
    elif isinstance(event_subset, list):
        if not isinstance(event, list):
            return result(AssertionError(f"Expected a list in event but found '{event}'."))
        for event_subset_item in event_subset:
            found_item = False
            for event_item in event:
                if assert_event_contains_subset(event_item, event_subset_item, dry_mode=True):
                    found_item = True
                    break
            if not found_item:
                return result(AssertionError(f"Item '{event_subset_item}' not found in {event}."))
    else:
        # {\n  \"command\": \"`whoami`\"\n} and {\"command\": \"`whoami`\"} are the same string
        try:
            j_event_subset = json.loads(event_subset)
            j_event = json.loads(event)
            if j_event_subset == j_event:
                return True
        except:
            pass
        if event_subset != event:
            return result(AssertionError(f"Value mismatch: {event_subset} != {event}"))

    return True


def generate_random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def get_response_status_code(response):
    if isinstance(response, http.client.HTTPResponse):
        return response.status
    else:
        if isinstance(response, requests.Response):
            return response.status_code
        else:
            return None


def assert_response_code_is(response, status_code, message=None):
    assert get_response_status_code(
        response) == status_code, f"Status codes are not the same: {get_response_status_code(response)} vs {status_code} {message}"


def assert_response_code_is_not(response, status_code, message=None):
    assert get_response_status_code(
        response) != status_code, f"Status code should be different from {status_code}. Message: {message}"


def assert_response_header_contains(response, header, value):
    assert header in response.headers, f"Header '{header}' is not part of response headers: {response.headers}"
    assert value in response.headers[header], f"Header '{header}' does not contain '{value}' but '{response.headers[header]}'"


def assert_response_body_contains(response, text, message=None):
    assert text in response.text, f"Test '{text}' is not part of response body: {response.text}. Message: {message}"


def assert_events_length_is(events, length):
    assert isinstance(events, list), "Error: Events is not a list."
    assert len(
        events) == length, f"Error: Events list contains {len(events)} elements and not {length} elements, {events}"


def assert_started_event_is_valid(event):
    assert_event_contains_subset(event, {"type": "started", "agent": {}})


def assert_event_contains_subset_file(event, event_subset_file):
    caller_frame = inspect.currentframe().f_back
    caller_filename = caller_frame.f_code.co_filename
    event_subset = None
    with open(os.path.join(os.path.dirname(caller_filename), event_subset_file), 'r') as file:
        event_subset = json.load(file)
    assert event_subset
    assert_event_contains_subset(event, event_subset)


def assert_line_contains_sensitive_data(line, line_number):
    patterns = {
        "SQL Query": r"select .* from|insert .* into",
        "URL Query String with Sensitive Param": r"(?i)(\?|&)(email|password|token|apikey|credit|ssn)=([^&\s]+)",
        "Basic Auth": r"(?i)basic\s+([a-zA-Z0-9]+:[a-zA-Z0-9]+)",
        "Password Param": r"password=[^&\s]+",
        "Bearer Token": r"(bearer\s+[A-Za-z0-9\-._~+/]+=*)",
        "Authorization Header": r"authorization:\s.*",
    }
    for pattern_name, pattern in patterns.items():
        if re.search(pattern, line):
            raise AssertionError(
                f"Line {line_number} contains '{pattern_name}': {line}")
