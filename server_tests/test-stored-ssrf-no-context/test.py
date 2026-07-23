
import time
import requests
from testlib import *
from core_api import CoreApi
import os

'''
Stored SSRF Attack Detection Test (No Request Context)

This test verifies that the firewall can detect and report stored SSRF attacks that occur 
outside of the original HTTP request context (e.g., in background threads, async tasks, or delayed jobs).

Test Steps:
1. Start mock IMDS server that adds IMDS IP address (169.254.169.254) to the lo interface
2. Set DNS to resolve evil-stored-ssrf-hostname to 169.254.169.254
3. Send POST request to /api/stored_ssrf_2 - returns 200 immediately (starts background thread)
4. Background thread waits 10 seconds, then makes SSRF request to evil-stored-ssrf-hostname
5. Wait up to 30 seconds for the firewall to detect the attack and submit event to core
6. Verify that a "detected_attack" event is submitted with attack details
'''

DNS_MOCK_URL = os.environ.get("TEST_DNS_MOCK_URL")


def set_dns_mapping(ip: str, hostname: str):
    if not DNS_MOCK_URL:
        raise RuntimeError("TEST_DNS_MOCK_URL is required for stored SSRF DNS mappings")

    response = requests.post(
        f"{DNS_MOCK_URL}/records",
        json={"hostname": hostname, "ip": ip},
        timeout=10,
    )
    response.raise_for_status()
    time.sleep(5)


def check_ssrf_with_event(collector, response_code, expected_json):
    start_events = c.get_events("detected_attack")
    response = s.post("/api/stored_ssrf_2", timeout=10)
    collector.soft_assert_response_code_is(
        response, response_code, f"[{response.text}]")

    c.wait_for_new_events(30, old_events_length=len(
        start_events), filter_type="detected_attack")

    all_events = c.get_events("detected_attack")
    new_events = all_events[len(start_events):]

    if not collector.soft_assert(
            len(new_events) >= 1,
            f"Events list contains {len(new_events)} elements, expected at least 1"):
        return

    try:
        assert_event_contains_subset_file(new_events[0], expected_json)
    except AssertionError as e:
        collector.add_failure(str(e))


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()
    set_dns_mapping("169.254.169.254", "evil-stored-ssrf-hostname")
    check_ssrf_with_event(collector, 200, "expect_detection_blocked.json")
    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
