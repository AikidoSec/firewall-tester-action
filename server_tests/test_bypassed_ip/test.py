
from testlib import *
from core_api import CoreApi

'''
Bypassed IPs allow certain IP addresses to completely bypass all Zen security features and protections.

This test verifies that:
1. Requests from bypassed IPs bypass rate limiting (multiple requests from same IP are not rate limited).
2. Requests from bypassed IPs bypass attack detection (path traversal, SQL injection, shell injection attacks are not blocked).
3. Requests from bypassed IPs do not generate API spec discovery data (routes are not included in heartbeat events).
4. Requests from bypassed IPs do not count towards attack statistics (attacksDetected and rateLimited remain 0).
5. Bypassed IPs work for single IPv4 addresses, IPv4 CIDR ranges, single IPv6 addresses, and IPv6 CIDR ranges.
'''


def get_request_data():
    url = "/api/create?name=test2&url_age=100"
    body = {
        "name": "test2",
        "age": 34
    }
    headers = {
        "Content-Type": "application/json",
    }
    return url, body, headers


def run_test(s: TestServer, c: CoreApi):
    # IPs that should be bypassed according to start_config.json
    bypass_ips = [
        {"ip": "93.184.216.34",    "type": "public IPv4"},
        {"ip": "203.0.113.42",      "type": "CIDR 203.0.113.0/24"},
        {"ip": "2606:2800:220:1:248:1893:25c8:1946",      "type": "single IPv6"},
        {"ip": "2001:db8:abcd:12:abcd::1", "type": "CIDR 2001:db8:abcd:0012::/64"},
    ]

    # Baseline events before sending any traffic for this test
    start_heartbeat_events = c.get_events("heartbeat")

    # Send multiple requests from each bypass IP and ensure they are never blocked
    for ip in bypass_ips:
        # ratelimit should be bypassed
        for _ in range(3):
            url, body, headers = get_request_data()
            headers_with_ip = {
                **headers,
                "X-Forwarded-For": ip["ip"]
            }
            response = s.post(url, body, headers=headers_with_ip)
            assert_response_code_is(
                response, 200, f"Request from bypass IP {ip['ip']} ({ip['type']}) should not be blocked"
            )

        # send some attacks
        # 1. path traversal attack
        response = s.get("/api/read?path=../secrets/key.txt",
                         headers={"X-Forwarded-For": ip["ip"]})
        assert_response_code_is(
            response, 200, f"Request should not be blocked: {response.text}")
        # 2. sql injection attack
        response = s.post(
            "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"}, headers={"X-Forwarded-For": ip["ip"]})
        assert_response_code_is(
            response, 200, f"Request should not be blocked: {response.text}")
        # 3. shell injection attack
        response = s.post(
            "/api/execute", {"userCommand": "whoami"}, headers={"X-Forwarded-For": ip["ip"]})
        assert_response_code_is(
            response, 200, f"Request should not be blocked: {response.text}")

        # # Wait a bit to give the agent time to potentially send heartbeat / stats
    c.wait_for_new_events(
        70, old_events_length=len(start_heartbeat_events), filter_type="heartbeat"
    )

    # # Ensure no new heartbeat events were created because bypassed IPs should not generate stats or API spec data
    all_heartbeat_events = c.get_events("heartbeat")
    new_heartbeat_events = all_heartbeat_events[len(start_heartbeat_events):]

    # routes should not contain  "method": "POST", "path": "/api/create",
    for route in new_heartbeat_events[0]["routes"]:
        assert "POST" not in route["method"] and "/api/create" not in route[
            "path"], f"Heartbeat event should not contain route POST /api/create: {route}, bypassed IPs should not generate stats or API spec data"

    assert new_heartbeat_events[0]["stats"]["requests"][
        "total"] == 1, f"Requests total should be 1, found {new_heartbeat_events[0]['stats']['requests']['total']}"
    # attacksDetected
    assert new_heartbeat_events[0]["stats"]["requests"]["attacksDetected"][
        "total"] == 0, f"Attacks detected should be 0, found {new_heartbeat_events[0]['stats']['requests']['attacksDetected']['total']}"
    # rateLimited
    assert new_heartbeat_events[0]["stats"]["requests"][
        "rateLimited"] == 0, f"Rate limited should be 0, found {new_heartbeat_events[0]['stats']['requests']['rateLimited']}"

    for stat in new_heartbeat_events[0]["stats"]["operations"].values():
        assert stat["attacksDetected"][
            "total"] == 0, f"Attacks detected should be 0: {stat}, found {stat['attacksDetected']['total']}"


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
