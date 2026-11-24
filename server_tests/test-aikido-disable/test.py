from testlib import *
from core_api import CoreApi

'''
Tests the AIKIDO_DISABLE environment variable functionality:

When AIKIDO_DISABLE is set to true, ALL Zen security features should be completely bypassed:

1. Attack Detection: SQL injection, path traversal, and shell injection attacks are NOT blocked
2. Rate Limiting: Multiple requests to /api/pets endpoint beyond configured limits (5 req/min) are NOT rate limited
3. User Blocking: Requests from blocked user ID "123456" are NOT blocked
4. Heartbeat Events: NO heartbeat events are sent (or if sent, contain no request statistics or route data)

This is a complete disable of all Aikido Zen functionality.
'''


def test_attacks_not_blocked(collector, s: TestServer):
    """Test that all attack types are allowed when AIKIDO_DISABLE=true"""

    # 1. SQL injection attack - should NOT be blocked
    response = s.post(
        "/api/create",
        {"name": "Malicious Pet', 'Gru from the Minions') --"},
        headers={"X-Forwarded-For": "1.2.3.4"}
    )
    collector.soft_assert_response_code_is(
        response, 200, "SQL injection should NOT be blocked when AIKIDO_DISABLE=true"
    )

    # 2. Path traversal attack - should NOT be blocked
    response = s.get(
        "/api/read?path=../secrets/key.txt",
        headers={"X-Forwarded-For": "1.2.3.4"}
    )
    collector.soft_assert_response_code_is(
        response, 200, "Path traversal should NOT be blocked when AIKIDO_DISABLE=true"
    )

    # 3. Shell injection attack - should NOT be blocked
    response = s.post(
        "/api/execute",
        {"userCommand": "whoami"},
        headers={"X-Forwarded-For": "1.2.3.4"}
    )
    collector.soft_assert_response_code_is(
        response, 200, "Shell injection should NOT be blocked when AIKIDO_DISABLE=true"
    )


def test_rate_limiting_not_enforced(collector, s: TestServer):
    """Test that rate limiting is NOT enforced when AIKIDO_DISABLE=true"""
    # Config has rate limit of 5 requests per minute for GET /api/pets
    # Send more than 5 requests - should all succeed
    for i in range(15):
        response = s.get(
            "/api/pets/",
            headers={"X-Forwarded-For": "13.14.15.16"}
        )
        collector.soft_assert_response_code_is(
            response, 200,
            f"Request {i+1} to /api/pets/ should NOT be rate limited when AIKIDO_DISABLE=true"
        )


def test_blocked_users_not_blocked(collector, s: TestServer):
    """Test that blocked user IDs are NOT blocked when AIKIDO_DISABLE=true"""

    # User "123456" is in blockedUserIds, but should not be blocked when disabled
    response = s.get(
        "/api/pets/",
        headers={"X-Forwarded-For": "1.2.3.4", "user": "123456"}
    )
    collector.soft_assert_response_code_is(
        response, 200,
        "Blocked user should NOT be blocked when AIKIDO_DISABLE=true"
    )


def assert_disabled_agent_reports_no_traffic(collector, s, heartbeats):
    s.get("/api/pets/")
    time.sleep(70)

    for report in heartbeats.read():
        requests = report.get("stats", {}).get("requests", {})
        collector.soft_assert(requests.get("total", 0) == 0, f"Disabled agent reported request statistics: {requests}")
        routes = report.get("routes", [])
        collector.soft_assert(routes is not None and len(routes) == 0, f"Disabled agent reported routes: {routes}")


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    heartbeats = c.track_heartbeats(collector)
    test_attacks_not_blocked(collector, s)
    test_rate_limiting_not_enforced(collector, s)
    test_blocked_users_not_blocked(collector, s)
    assert_disabled_agent_reports_no_traffic(collector, s, heartbeats)

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
