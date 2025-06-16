import datetime
import time
import requests
import argparse
from core_api import CoreApi
from requests.adapters import HTTPAdapter, Retry
import json
import subprocess

s = requests.Session()
retries = Retry(connect=10,
                backoff_factor=1)

s.mount('http://', HTTPAdapter(max_retries=retries))


def localhost_get_request(port, route="", headers={}, benchmark=False):
    global benchmarks, s

    start_time = datetime.datetime.now()

    r = s.get(f"http://localhost:{port}{route}", headers=headers)

    end_time = datetime.datetime.now()
    delta = end_time - start_time
    elapsed_ms = delta.total_seconds() * 1000

    if benchmark:
        benchmarks.append(elapsed_ms)

    time.sleep(0.001)
    return r


def localhost_post_request(port, route, data, headers={}, benchmark=False):
    global benchmarks, s

    start_time = datetime.datetime.now()

    r = s.post(f"http://localhost:{port}{route}", json=data, headers=headers)
    end_time = datetime.datetime.now()
    delta = end_time - start_time
    elapsed_ms = delta.total_seconds() * 1000

    if benchmark:
        benchmarks.append(elapsed_ms)

    time.sleep(0.001)
    return r


def init_server_and_core():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server_port", type=int, required=True)
    parser.add_argument("--token", type=str, required=True)
    parser.add_argument("--core_port", type=int, default=3000)
    parser.add_argument("--config_update_delay", type=int, default=60)
    args = parser.parse_args()

    server = TestServer(port=args.server_port, token=args.token)
    core = CoreApi(token=args.token, core_url=f"http://localhost:{args.core_port}",
                   config_update_delay=args.config_update_delay)

    return args, server, core


class TestServer:
    def __init__(self, port: int, token: str):
        self.port = port
        self.token = token

    def get(self, route="", headers={}, benchmark=False):
        return localhost_get_request(self.port, route, headers, benchmark)

    def post(self, route="", data={}, headers={}, benchmark=False):
        return localhost_post_request(self.port, route, data, headers, benchmark)

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


def assert_response_code_is(response, status_code):
    assert response.status_code == status_code, f"Status codes are not the same: {response.status_code} vs {status_code}"


def assert_response_header_contains(response, header, value):
    assert header in response.headers, f"Header '{header}' is not part of response headers: {response.headers}"
    assert value in response.headers[header], f"Header '{header}' does not contain '{value}' but '{response.headers[header]}'"


def assert_response_body_contains(response, text):
    assert text in response.text, f"Test '{text}' is not part of response body: {response.text}"


def assert_events_length_is(events, length):
    assert isinstance(events, list), "Error: Events is not a list."
    assert len(
        events) == length, f"Error: Events list contains {len(events)} elements and not {length} elements."


def assert_started_event_is_valid(event):
    assert_event_contains_subset(event, {"type": "started", "agent": {}})


def assert_event_contains_subset_file(event, event_subset_file):
    event_subset = None
    with open(event_subset_file, 'r') as file:
        event_subset = json.load(file)
    assert event_subset
    assert_event_contains_subset(event, event_subset)
