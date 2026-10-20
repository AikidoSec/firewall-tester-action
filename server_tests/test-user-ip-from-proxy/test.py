import http.client
import ipaddress
import time
from testlib import *
from core_api import CoreApi

'''
Tests that when AIKIDO_TRUST_PROXY=true and AIKIDO_CLIENT_IP_HEADER=X-Real-IP,
the user's lastIpAddress in heartbeat events reflects the resolved client IP
from the proxy header — not the raw TCP connection IP (e.g. Docker bridge).

1. Send requests with a user header and X-Real-IP proxy header.
2. Wait for a heartbeat event.
3. Verify the user's lastIpAddress matches X-Real-IP, not the container IP.
'''

REAL_CLIENT_IP = "11.22.33.44"
USER_ID = "42"
SOCKET_USER_ID = "43"


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    start_events = c.get_events("heartbeat")

    for _ in range(3):
        response = s.get("/api/pets/", headers={
            "user": USER_ID,
            "X-Real-IP": REAL_CLIENT_IP
        })
        collector.soft_assert_response_code_is(response, 200)
        time.sleep(0.5)

    connection = http.client.HTTPConnection(TEST_SERVER_HOST, s.port, timeout=10)
    try:
        connection.connect()
        socket_ip = connection.sock.getsockname()[0]
        server_ip = connection.sock.getpeername()[0]
        assert socket_ip != server_ip, "Client and server IPs must differ for the socket IP check"
        connection.request("GET", "/api/pets/", headers={"user": SOCKET_USER_ID})
        response = connection.getresponse()
        response.read()
        collector.soft_assert_response_code_is(response, 200)
    finally:
        connection.close()

    traffic_finished_at = int(time.time() * 1000)
    heartbeat, candidates = c.wait_for_heartbeat_after(
        160, len(start_events), traffic_finished_at,
        predicate=lambda event: {USER_ID, SOCKET_USER_ID}.issubset(
            str(user.get("id")) for user in (event.get("users") or []))
    )

    if not collector.soft_assert(
            heartbeat is not None,
            f"Expected a heartbeat produced after test traffic, got {len(candidates)} candidate heartbeat(s)"):
        collector.raise_if_failures()
        return

    users = heartbeat.get("users", [])

    if not collector.soft_assert(len(users) >= 1, f"Expected at least 1 user in heartbeat, got {len(users)}"):
        collector.raise_if_failures()
        return

    for user_id, expected_ip in ((USER_ID, REAL_CLIENT_IP), (SOCKET_USER_ID, socket_ip)):
        target_user = next((user for user in users if str(user.get("id")) == user_id), None)
        if not collector.soft_assert(target_user is not None, f"User {user_id} not found in heartbeat users: {users}"):
            continue

        last_ip = target_user.get("lastIpAddress", "")
        try:
            actual_ip = ipaddress.ip_address(last_ip)
        except ValueError:
            collector.add_failure(f"User {user_id} has an invalid lastIpAddress: {last_ip!r}")
            continue
        actual_ip = getattr(actual_ip, "ipv4_mapped", None) or actual_ip
        collector.soft_assert(
            actual_ip == ipaddress.ip_address(expected_ip),
            f"User {user_id} lastIpAddress should be '{expected_ip}', but got '{last_ip}'")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
