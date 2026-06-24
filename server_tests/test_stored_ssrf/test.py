
import time
import requests
from testlib import *
from core_api import CoreApi
import os

'''
Stored SSRF Attack Detection Test

This test verifies that the firewall can detect and block stored SSRF attacks targeting IMDS endpoints.

Stored SSRF attacks happen when an attacker can alter how hostnames are resolved by
e.g. having spoofed DNS.
If the hostname is a trusted host (like metadata.goog), there was no spoofing of hostnames,
so it's not a stored SSRF attack.

Test Steps:
1. Start mock IMDS server that adds multiple IP addresses (169.254.169.254, 100.100.100.200, fd00:ec2::254) to the lo interface
2. Set DNS to resolve evil-stored-ssrf-hostname to 169.254.169.254
3. Send POST request to /api/stored_ssrf - should be blocked (500 response)
4. Verify that a "detected_attack" event is submitted to core with blocking details
5. Update runtime config to disable blocking (forceProtectionOff)
6. Send POST request to /api/stored_ssrf - should not be blocked (200 response)
7. Verify that no event is submitted to core
8. Restore original runtime config
9. Send POST request to /api/stored_ssrf - should be blocked again (500 response)
10. Verify that a "detected_attack" event is submitted to core
11. Test multiple IMDS IP addresses (both IPv4 and IPv6 formats):
    - IPv4: 169.254.169.254, 100.100.100.200
    - IPv6: ::ffff:169.254.169.254, ::ffff:100.100.100.200, fd00:ec2::254, and various canonical forms
13. For each IP, update DNS and verify that requests are blocked

'''

DNS_MOCK_URL = os.environ.get("TEST_DNS_MOCK_URL")
SKIP_IPV6_SSRF = os.environ.get("SKIP_IPV6_SSRF", "0") == "1"


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


def check_ssrf_with_event(collector, s, c, response_code, expected_json, num_events: int = 1):
    start_events = c.get_events("detected_attack")
    response = s.post("/api/stored_ssrf", timeout=10)
    collector.soft_assert_response_code_is(
        response, response_code, f"[{response.text}]")

    c.wait_for_new_events(5, old_events_length=len(
        start_events), filter_type="detected_attack")

    all_events = c.get_events("detected_attack")
    new_events = all_events[len(start_events):]

    # Prerequisite: need at least num_events to check contents
    if not collector.soft_assert(len(new_events) >= num_events, f"Expected at least {num_events} new event(s), got {len(new_events)}"):
        return
    try:
        if num_events == 1:
            assert_event_contains_subset_file(new_events[0], expected_json)
    except AssertionError as e:
        collector.add_failure(str(e))


def check_ssrf_bypassed_ip(collector, s, ip: str):
    response = s.post("/api/stored_ssrf", timeout=10,
                      headers={"X-Forwarded-For": ip})
    collector.soft_assert_response_code_is(
        response, 200, f"[{response.text}] Bypassed IP {ip} should not be blocked")


def check_stored_ssrf(collector, s, ip: str):
    response = s.post("/api/stored_ssrf", timeout=10)
    collector.soft_assert_response_code_is(
        response, 500, f"evil-stored-ssrf-hostname -> {ip} [{response.text}]")
    collector.soft_assert_response_body_contains(
        response, "blocked", f"evil-stored-ssrf-hostname -> {ip} [{response.text}]")


def check_stored_ssrf_with_url(collector, s, domain: str, url: int):
    response = s.post("/api/stored_ssrf", {"urlIndex": url})
    collector.soft_assert_response_code_is(
        response, 200, f"IP addresses for Google Cloud Metadata Service or direct IMDS IP access should be allowed: {domain} ->  169.254.169.254 [{response.text}]")
    collector.soft_assert_response_body_contains(
        response, "Success", f"IP addresses for Google Cloud Metadata Service or direct IMDS IP access should be allowed: {domain} -> 169.254.169.254 [{response.text}]")


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    set_dns_mapping("169.254.169.254", "evil-stored-ssrf-hostname")

    check_ssrf_with_event(collector, s, c, 500,
                          "expect_detection_blocked.json")

    # test with allowedIPAddresses, should not be blocked
    check_ssrf_bypassed_ip(collector, s, "93.184.216.34")

    c.update_runtime_config_file("change_config_disable_blocking.json")
    check_ssrf_with_event(collector, s, c,
                          200, "expect_detection_not_blocked.json", num_events=0)

    c.update_runtime_config_file("start_config.json")
    check_ssrf_with_event(collector, s, c, 500,
                          "expect_detection_blocked.json")

    IDMS_IPS_V4 = [
        "169.254.169.254",
        "100.100.100.200",
    ]

    IDMS_IPS_V6 = [
        "::ffff:169.254.169.254",
        "::ffff:100.100.100.200",
        "fd00:ec2::254",
        "0000:0000:0:0000:0000:ffff:a9fe:a9fe",
        "0:0:0:0:0:ffff:a9fe:a9fe",
        "0::0:0:0:ffff:a9fe:a9fe",
        "0:0:0000:0000:0000:ffff:6464:64c8",
        "0:0:0::ffff:6464:64c8"
        #  "fd00:ec2:0:0000:0000:0:0000:254",
        #  "fd00:ec2:0:0:0:0::254"
    ]

    imds_ips = IDMS_IPS_V4 if SKIP_IPV6_SSRF else IDMS_IPS_V4 + IDMS_IPS_V6
    for ip in imds_ips:
        set_dns_mapping(ip, "evil-stored-ssrf-hostname")
        check_stored_ssrf(collector, s, ip)

    # metadata.google.internal (url=1) is a trusted host, should not be blocked
    check_stored_ssrf_with_url(collector, s, "metadata.google.internal", 1)

    # metadata.goog (url=2) is a trusted host, should not be blocked
    check_stored_ssrf_with_url(collector, s, "metadata.goog", 2)

    # 169.254.169.254 (url=3) is an IP, not a hostname resolution spoofing case, should not be blocked
    check_stored_ssrf_with_url(collector, s, "169.254.169.254", 3)

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
