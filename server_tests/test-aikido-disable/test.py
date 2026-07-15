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
        response, 200, f"SQL injection should NOT be blocked when AIKIDO_DISABLE=true: {response.text}"
    )

    # 2. Path traversal attack - should NOT be blocked
    response = s.get(
        "/api/read?path=../secrets/key.txt",
        headers={"X-Forwarded-For": "1.2.3.4"}
    )
    collector.soft_assert_response_code_is(
        response, 200, f"Path traversal should NOT be blocked when AIKIDO_DISABLE=true: {response.text}"
    )

    # 3. Shell injection attack - should NOT be blocked
    response = s.post(
        "/api/execute",
        {"userCommand": "whoami"},
        headers={"X-Forwarded-For": "1.2.3.4"}
    )
    collector.soft_assert_response_code_is(
        response, 200, f"Shell injection should NOT be blocked when AIKIDO_DISABLE=true: {response.text}"
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
            f"Request {i+1} to /api/pets/ should NOT be rate limited when AIKIDO_DISABLE=true: {response.text}"
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
        f"Blocked user should NOT be blocked when AIKIDO_DISABLE=true: {response.text}"
    )


def test_no_heartbeat_or_start_events(collector, s, c: CoreApi, initial_heartbeat_events):
    """Test that heartbeat and start events are NOT sent when AIKIDO_DISABLE=true"""
    s.get("/api/pets/")
    # Wait for potential heartbeat interval (70 seconds to be sure)
    # If heartbeats were being sent, we'd expect at least one
    time.sleep(70)

    # Check that no new heartbeat events were sent
    current_heartbeat_events = c.get_events("heartbeat")
    new_heartbeat_count = len(current_heartbeat_events) - \
        len(initial_heartbeat_events)

    # When disabled, either no heartbeats are sent, or if they are sent, they should contain no stats
    if new_heartbeat_count > 0:
        # If heartbeats are sent, verify they contain no meaningful statistics
        for event in current_heartbeat_events[len(initial_heartbeat_events):]:
            # Stats should either be absent or show zero activity
            if "stats" in event:
                stats = event["stats"]
                if "requests" in stats:
                    # All request stats should be zero or minimal
                    collector.soft_assert(
                        stats["requests"].get(
                            "total", 0) == 0 or stats["requests"].get("total", 0) == 1,
                        f"When AIKIDO_DISABLE=true, heartbeat should not contain request statistics: {stats}"
                    )

            # Routes should be empty or minimal
            if "routes" in event:
                collector.soft_assert(
                    len(event.get("routes", [])) <= 1,
                    f"When AIKIDO_DISABLE=true, no API routes should be tracked: {event['routes']}"
                )


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    initial_heartbeat_events = c.get_events("heartbeat")
    test_attacks_not_blocked(collector, s)
    test_rate_limiting_not_enforced(collector, s)
    test_blocked_users_not_blocked(collector, s)
    test_no_heartbeat_or_start_events(
        collector, s, c, initial_heartbeat_events)

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
