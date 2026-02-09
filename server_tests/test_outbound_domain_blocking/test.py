from testlib import *
from core_api import CoreApi
import socket
'''
Tests the outbound domain blocking feature:

1. Tests that explicitly blocked domains are always blocked
2. Tests that bypassed IPs (allowedIPAddresses) can access any domain including blocked ones and new domains
3. Tests that forceProtectionOff does not affect outbound domain blocking
4. Tests that allowed domains can be accessed when blockNewOutgoingRequests is true
5. Tests that new/unknown domains are blocked when blockNewOutgoingRequests is true
6. Tests case-insensitive hostname matching (uppercase and mixed case)
7. Tests IDN normalization and bypass prevention:
   - Punycode requests blocked when Unicode domain is in blocklist (core only accepts Unicode hostnames)
   - Allowed IDN domains work with both Unicode and Punycode forms
   - URL percent-encoding bypass attempts are blocked
8. Tests heartbeat events:
   - Blocked domains are reported in heartbeat events
   - Bypassed IPs do not report domains in heartbeat events
   - Allowed domains are reported in heartbeat events
9. Tests that new domains are allowed when blockNewOutgoingRequests is false
10. Tests that explicitly blocked domains are still blocked when blockNewOutgoingRequests is false
11. Tests that detection mode (block: false) doesn't block
'''


def start_mock_servers(target_container_name: str):
    path = os.path.join(os.path.dirname(__file__), "mock-server.sh")

    subprocess.run(
        f"docker run -d --name mock-server-{target_container_name} -v {path}:/mock-server.sh:ro --network container:{target_container_name} --cap-add=NET_ADMIN python:3.12-alpine sh /mock-server.sh", shell=True)
    i = 0
    while True:
        time.sleep(1)
        if subprocess.run(
                f"docker ps | grep mock-server-{target_container_name} | grep Up", shell=True).returncode == 0:
            break
        time.sleep(1)
        i += 1
        if i > 20:
            raise Exception(
                f"Mock server did not start after {i} seconds")


def set_etc_hosts(target_container_name: str, ip: str, hostname: str):
    subprocess.run(
        f"docker exec  -u 0 {target_container_name} sh -c 'echo {ip} {hostname} >> /etc/hosts'", shell=True)


def test_explicitly_blocked_domain(collector, s: TestServer, c: CoreApi):

    start_events = c.get_events("heartbeat")

    """Test that explicitly blocked domains are always blocked"""
    response = s.post("/api/request",
                      {"url": "http://evil.example.com/test"})
    collector.soft_assert_response_code_is(
        response, 500, f"{response.text} - explicitly blocked domain evil.example.com should be blocked")
    collector.soft_assert_response_body_contains(
        response, "blocked an outbound connection")

    """ Bypassed IP address tests that should be allowed """
    response = s.post(
        "/api/request", {"url": "http://evil.example.com/test"}, headers={"X-Forwarded-For": "1.2.3.4"})
    collector.soft_assert_response_code_is_not(
        response, 500, f"{response.text} - bypassed IP address should be allowed for evil.example.com")

    response = s.post(
        "/api/request", {"url": "http://domain1.example.com/test"}, headers={"X-Forwarded-For": "1.2.3.4"})
    collector.soft_assert_response_code_is_not(
        response, 500, f"{response.text} - bypassed IP address should be allowed for new domains")

    """Test that force protection off does not affect outbound domain blocking"""
    response = s.post("/api/request2",
                      {"url": "http://evil.example.com/test"})
    collector.soft_assert_response_code_is(
        response, 500, f"{response.text} - force protection off should not affect outbound domain blocking")
    collector.soft_assert_response_body_contains(
        response, "blocked an outbound connection")

    """Test that allowed domains can be accessed when blockNewOutgoingRequests is true"""
    response = s.post("/api/request", {"url": "http://safe.example.com"})
    collector.soft_assert_response_code_is(
        response, 200, f"{response.text} - allowed domain should be allowed when blockNewOutgoingRequests is true")

    """Test that new/unknown domains are blocked when blockNewOutgoingRequests is true"""
    response = s.post("/api/request", {"url": "http://domain2.example.com"})
    collector.soft_assert_response_code_is(
        response, 500, f"{response.text} - new domain should be blocked when blockNewOutgoingRequests is true")
    collector.soft_assert_response_body_contains(
        response, "blocked an outbound connection")

    """Test that hostname matching is case-insensitive"""
    # Test with uppercase hostname
    response = s.post("/api/request", {"url": "http://EVIL.EXAMPLE.COM"})
    collector.soft_assert_response_code_is(
        response, 500, f"{response.text} - uppercase hostname EVIL.EXAMPLE.COM should be blocked (case-insensitive matching)")
    collector.soft_assert_response_body_contains(
        response, "blocked an outbound connection")

    # Test with mixed case
    response = s.post("/api/request", {"url": "http://Evil.Example.Com"})
    collector.soft_assert_response_code_is(
        response, 500, f"{response.text} - mixed case hostname Evil.Example.Com should be blocked (case-insensitive matching)")
    collector.soft_assert_response_body_contains(
        response, "blocked an outbound connection")

    """Test Punycode bypass attempts - Unicode domain blocked, Punycode request"""
    # böse.example.com is blocked in config as Unicode
    # xn--bse-sna.example.com is the Punycode encoding of "böse.example.com"
    response = s.post(
        "/api/request", {"url": "http://xn--bse-sna.example.com"})
    collector.soft_assert_response_code_is(
        response, 500, f"{response.text} - Punycode request xn--bse-sna.example.com should be blocked when Unicode domain böse.example.com is in blocklist")
    collector.soft_assert_response_body_contains(
        response, "blocked an outbound connection")

    """Test Unicode domain blocked - Unicode request"""
    # münchen.example.com is blocked in config as Unicode (core only accepts Unicode hostnames)
    # münchen.example.com is the Unicode form
    response = s.post("/api/request", {"url": "http://münchen.example.com"})
    collector.soft_assert_response_code_is(
        response, 500, f"{response.text} - Unicode request münchen.example.com should be blocked when Unicode domain is in blocklist")
    collector.soft_assert_response_body_contains(
        response, "blocked an outbound connection")

    """Test allowed IDN domains work with both Unicode and Punycode forms"""
    # münchen-allowed.example.com is allowed in config as Unicode
    # Should work with Unicode form
    response = s.post(
        "/api/request", {"url": "http://münchen-allowed.example.com"})
    collector.soft_assert_response_code_is(
        response, 200, f"{response.text} - allowed Unicode domain münchen-allowed.example.com should be accessible")

    # Should also work with Punycode form (xn--mnchen-allowed-gsb.example.com)
    response = s.post(
        "/api/request", {"url": "http://xn--mnchen-allowed-gsb.example.com"})
    collector.soft_assert_response_code_is(
        response, 200, f"{response.text} - allowed Punycode domain xn--mnchen-allowed-gsb.example.com should be accessible")

    """Test URL percent-encoding bypass attempts"""
    # böse.example.com is blocked -  percent-encoded ö (%C3%B6)
    # b%C3%B6se.example.com should be normalized to böse.example.com
    response = s.post("/api/request", {"url": "http://b%C3%B6se.example.com"})
    collector.soft_assert_response_body_contains(
        response, "\"ok\"", f"{response.text} - percent-encoded hostname b%C3%B6se.example.com should not be allowed")

    c.wait_for_new_events(70, old_events_length=len(
        start_events), filter_type="heartbeat")

    # test heartbeat event ()
    all_events = c.get_events("heartbeat")
    new_events = all_events[len(start_events):]

    # Prerequisite: need exactly 1 heartbeat event to check contents
    if not collector.soft_assert(len(new_events) == 1, f"Expected 1 new heartbeat event, got {len(new_events)}"):
        return

    heartbeat = new_events[0]
    # assrt hostname in heartbeat
    collector.soft_assert("hostnames" in heartbeat, "hostnames should be in heartbeat")
    if "hostnames" in heartbeat:
        hostnames = heartbeat["hostnames"]

        collector.soft_assert(any(hostname["hostname"] == "domain2.example.com" for hostname in hostnames), "domain2.example.com should be in hostnames, blocked domains still need to be reported in the heartbeat event")
        # domain1.example.com should not be in hostnames
        collector.soft_assert(not any(
            hostname["hostname"] == "domain1.example.com" for hostname in hostnames), "domain1.example.com should not be in hostnames, Bypassed IPs should not report domains")
        # safe.example.com
        collector.soft_assert(any(hostname["hostname"] == "safe.example.com" for hostname in hostnames), "safe.example.com should be in hostnames, allowed domains should be reported in the heartbeat event")


def test_new_domain_allowed_when_flag_disabled(collector, s: TestServer, c: CoreApi):
    """Test that new domains are allowed when blockNewOutgoingRequests is false"""
    c.update_runtime_config_file("config_disable_block_new.json")

    response = s.post("/api/request",
                      {"url": "http://another-unknown.example.com"})
    collector.soft_assert_response_code_is(
        response, 200, f"{response.text} - new domain should be allowed")

    """Test that explicitly blocked domains are still blocked when blockNewOutgoingRequests is false"""
    response = s.post("/api/request", {"url": "http://evil.example.com"})
    collector.soft_assert_response_code_is(
        response, 500, f"{response.text} - explicitly blocked domain evil.example.com should still be blocked even when blockNewOutgoingRequests is false")
    collector.soft_assert_response_body_contains(
        response, "blocked an outbound connection")


def test_detection_mode(collector, s: TestServer, c: CoreApi):
    """Test that detection mode (block: false) doesn't block"""
    c.update_runtime_config_file("config_no_blocking.json")

    response = s.post("/api/request", {"url": "http://evil.example.com"})
    collector.soft_assert_response_code_is(
        response, 200, f"{response.text} - detection mode (block: false) should not block requests to evil.example.com")


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    test_explicitly_blocked_domain(collector, s, c)
    test_new_domain_allowed_when_flag_disabled(collector, s, c)
    test_detection_mode(collector, s, c)

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    target_container_name = "test_outbound_domain_blocking"
    domain_names = [
        "evil.example.com",
        "domain1.example.com",
        "domain2.example.com",
        "safe.example.com",
        "another-unknown.example.com",
        "unknown.example.com",
        "xn--bse-sna.example.com",
        "xn--mnchen-3ya.example.com",
        "xn--mnchen-allowed-gsb.example.com"
    ]
    ip = "11.22.33.44"
    try:
        start_mock_servers(target_container_name)
        for domain_name in domain_names:
            set_etc_hosts(target_container_name, ip, domain_name)
        run_test(s, c)
    finally:
        subprocess.run(
            f"docker rm -f mock-server-{target_container_name}", shell=True)
