
import time
from testlib import *
from core_api import CoreApi
import os

'''
Stored SSRF Attack Detection Test

This test verifies that the firewall can detect and block stored SSRF attacks targeting IMDS endpoints.

Stored SSRF attacks happen when an attacker can alter how hostnames are resolved by
e.g. having inserted an entry in /etc/hosts, or having spoofed the DNS.
If the hostname is a trusted host (like metadata.goog), there was no spoofing of hostnames,
so it's not a stored SSRF attack.

Test Steps:
1. Save original /etc/hosts file from target container
2. Start mock IMDS server that adds multiple IP addresses (169.254.169.254, 100.100.100.200, fd00:ec2::254) to the lo interface
3. Set /etc/hosts to resolve evil-stored-ssrf-hostname to 169.254.169.254
4. Send POST request to /api/stored_ssrf - should be blocked (500 response)
5. Verify that a "detected_attack" event is submitted to core with blocking details
6. Update runtime config to disable blocking (forceProtectionOff)
7. Send POST request to /api/stored_ssrf - should not be blocked (200 response)
8. Verify that no event is submitted to core
9. Restore original runtime config
10. Send POST request to /api/stored_ssrf - should be blocked again (500 response)
11. Verify that a "detected_attack" event is submitted to core
12. Test multiple IMDS IP addresses (both IPv4 and IPv6 formats):
    - IPv4: 169.254.169.254, 100.100.100.200
    - IPv6: ::ffff:169.254.169.254, ::ffff:100.100.100.200, fd00:ec2::254, and various canonical forms
13. For each IP, update /etc/hosts and verify that requests are blocked

'''


def save_etc_hosts(target_container_name: str):
    subprocess.run(
        f"docker exec  -u 0 {target_container_name} sh -c 'cp /etc/hosts /tmp/hosts.original'", shell=True)
    subprocess.run(
        f"docker exec  -u 0 {target_container_name} sh -c 'echo 169.254.169.254 metadata.google.internal >> /tmp/hosts.original'", shell=True)
    subprocess.run(
        f"docker exec  -u 0 {target_container_name} sh -c 'echo 169.254.169.254 metadata.goog >> /tmp/hosts.original'", shell=True)
    time.sleep(1)


def set_etc_hosts(target_container_name: str, ip: str, hostname: str):
    subprocess.run(
        f"docker exec  -u 0 {target_container_name} sh -c 'cat /tmp/hosts.original > /etc/hosts && echo {ip} {hostname} >> /etc/hosts'", shell=True)
    time.sleep(5)


def start_mock_servers(target_container_name: str):
    path = os.path.join(os.path.dirname(__file__), "mock-imds.py")
    subprocess.run(
        f"docker run -d --name {target_container_name}-mock-imds -v {path}:/mock-imds.py:ro --network container:{target_container_name} --cap-add NET_ADMIN python:3.12-alpine sh -c 'apk add --no-cache iproute2 && python /mock-imds.py 169.254.169.254 100.100.100.200 fd00:ec2::254'", shell=True)
    i = 0
    while True:
        time.sleep(1)
        if subprocess.run(
                f"docker ps | grep {target_container_name}-mock-imds | grep Up", shell=True).returncode == 0:
            break
        time.sleep(1)
        i += 1
        if i > 20:
            raise Exception(
                f"Mock IMDS server did not start after {i} seconds")


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


def run_test(s: TestServer, c: CoreApi, target_container_name: str):
    collector = AssertionCollector()

    save_etc_hosts(target_container_name)
    set_etc_hosts(target_container_name, "169.254.169.254",
                  "evil-stored-ssrf-hostname")

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

    for ip in IDMS_IPS_V4 + IDMS_IPS_V6:
        set_etc_hosts(target_container_name, ip, "evil-stored-ssrf-hostname")
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
    target_container_name = "test_stored_ssrf"
    try:
        start_mock_servers(target_container_name)
        run_test(s, c, target_container_name)
    finally:
        subprocess.run(
            f"docker rm -f {target_container_name}-mock-imds", shell=True)
