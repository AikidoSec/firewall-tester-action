
from testlib import *
from core_api import CoreApi

'''
Bypassed IPs allow certain IP addresses to bypass all Zen security features and protections.

This test verifies that:
1. Requests from bypassed IPs bypass rate limiting (multiple requests from same IP are not rate limited).
2. Requests from bypassed IPs bypass attack detection (path traversal, SQL injection, shell injection attacks are not blocked).
3. Requests from bypassed IPs bypass bot blocking (requests with blocked user agents are not blocked).
4. Requests from bypassed IPs bypass geo blocking (requests from blocked IP ranges are not blocked).
5. Requests from bypassed IPs bypass route-level Admin IP restrictions (endpoint-level `allowedIPAddresses` when a specific allowlist is configured).
6. Requests from bypassed IPs bypass blocked user IDs (blockedUserIds).
7. Requests from bypassed IPs do not generate API spec discovery data (routes are not included in heartbeat events).
8. Requests from bypassed IPs do not count towards attack statistics (attacksDetected and rateLimited remain 0).
9. Bypassed IPs work for single IPv4 addresses, IPv4 CIDR ranges, single IPv6 addresses, and IPv6 CIDR ranges.
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
    collector = AssertionCollector()

    # IPs that should be bypassed according to start_config.json
    bypass_ips = [
        {"ip": "93.184.216.34",    "type": "public IPv4"},
        {"ip": "23.45.67.89",      "type": "CIDR 23.45.67.89/24"},
        {"ip": "::ffff:23.45.67.89",
            "type": "IPv4-mapped IPv6 address (in 23.45.67.89/24 range)"},
        {"ip": "2606:2800:220:1:248:1893:25c8:1946",      "type": "single IPv6"},
        {"ip": "2001:0db9:abcd:1234::5678", "type": "CIDR 2001:0db9:abcd:1234::/64"},
    ]

    heartbeats = c.track_heartbeats(collector)

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
            collector.soft_assert_response_code_is(
                response, 200, f"Request from bypass IP {ip['ip']} ({ip['type']}) should not be blocked"
            )

        # send attacks
        # 1. path traversal attack
        response = s.get("/api/read?path=../secrets/key.txt",
                         headers={"X-Forwarded-For": ip["ip"]})
        collector.soft_assert_response_code_is(
            response, 200, "Request should not be blocked")
        # 2. sql injection attack
        response = s.post(
            "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"}, headers={"X-Forwarded-For": ip["ip"]})
        collector.soft_assert_response_code_is(
            response, 200, "Request should not be blocked")
        # 3. shell injection attack
        response = s.post(
            "/api/execute", {"userCommand": "whoami"}, headers={"X-Forwarded-For": ip["ip"]})
        collector.soft_assert_response_code_is(
            response, 200, "Request should not be blocked")

        # 4. bot blocking should be bypassed (send request with blocked user agent)
        # Using pattern like "1234googlebot1234" which matches the blockedUserAgents pattern "Googlebot"
        response = s.get(
            "/test_ratelimiting_2", headers={"X-Forwarded-For": ip["ip"], "User-Agent": "1234googlebot1234"})
        collector.soft_assert_response_code_is(
            response, 200, f"Request with blocked user agent should not be blocked from bypass IP {ip['ip']} ({ip['type']})")

        # 5. geo blocking should be bypassed (send request from IP that would normally be geo-blocked)
        # Note: Some bypass IPs (93.184.216.34 and 23.45.67.89) are in blockedIPAddresses ranges in start_firewall.json, so they should still work
        response = s.get(
            "/api/pets/", headers={"X-Forwarded-For": ip["ip"]})
        collector.soft_assert_response_code_is(
            response, 200, f"Request from bypass IP {ip['ip']} ({ip['type']}) should bypass geo blocking")

        # 6. route-level Admin IP restrictions should be bypassed (endpoint-level `allowedIPAddresses`)
        # The /test_ratelimiting_1 endpoint has allowedIPAddresses: ["185.245.255.212"], but bypassed IPs should still access it
        response = s.get(
            "/test_ratelimiting_1", headers={"X-Forwarded-For": ip["ip"]})
        collector.soft_assert_response_code_is(
            response, 200, f"Request from bypass IP {ip['ip']} ({ip['type']}) should bypass route-level Admin IP restrictions")

        # # 7. blocked user IDs should be bypassed (blockedUserIds)
        # User "789" is in blockedUserIds, but requests from bypassed IPs should still work
        response = s.get(
            "/api/pets/", headers={"X-Forwarded-For": ip["ip"], "user": "789"})
        collector.soft_assert_response_code_is(
            response, 200, f"Request from bypass IP {ip['ip']} ({ip['type']}) should bypass blocked user IDs")

    reports = heartbeats.wait_for_next_report()
    requests_total = heartbeats.requests_since_startup()
    collector.soft_assert(
        requests_total == 1,
        f"Only the initial request should be counted, found {requests_total}")
    for route in heartbeats.entries("routes"):
        collector.soft_assert(
            not ("POST" in route["method"] and "/api/create" in route["path"]),
            f"Heartbeat event should not contain route POST /api/create: {route}, bypassed IPs should not generate stats or API spec data")
    attacks = heartbeats.attacks_detected()
    collector.soft_assert(attacks == 0, f"Attacks detected should be 0, found {attacks}")
    for report in reports:
        stats = report["stats"]
        rate_limited = stats["requests"].get("rateLimited")
        collector.soft_assert(rate_limited == 0, f"Expected rateLimited to be 0, got {rate_limited}")
        operations = stats.get("operations")
        if collector.soft_assert(isinstance(operations, dict), f"Expected operations in heartbeat stats, got {operations}"):
            for name, operation in operations.items():
                detected = operation.get("attacksDetected", {}).get("total")
                collector.soft_assert(detected == 0, f"Expected zero attacks for {name}, got {detected}")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
