import socket
import time
from testlib import *
from core_api import CoreApi

REAL_CLIENT_IP = "11.22.33.44"
USER_ID_WITH_PROXY_HEADER = "42"
USER_ID_WITHOUT_PROXY_HEADER = "43"


def run_test(s: TestServer, c: CoreApi):
    start_events = c.get_events("heartbeat")

    response = s.get("/api/pets/", headers={
        "user": USER_ID_WITH_PROXY_HEADER,
        "X-Real-IP": REAL_CLIENT_IP
    })
    assert_response_code_is(response, 200)

    with socket.create_connection((TEST_SERVER_HOST, s.port), timeout=10) as connection:
        client_ip = connection.getsockname()[0]
        server_ip = connection.getpeername()[0]
        assert client_ip != server_ip, "Client and server IPs must differ for this test"

    response = s.get("/api/pets/", headers={"user": USER_ID_WITHOUT_PROXY_HEADER})
    assert_response_code_is(response, 200)

    expected_ips = {
        USER_ID_WITH_PROXY_HEADER: REAL_CLIENT_IP,
        USER_ID_WITHOUT_PROXY_HEADER: client_ip,
    }

    traffic_finished_at = int(time.time() * 1000)
    heartbeat, candidates = c.wait_for_heartbeat_after(
        160, len(start_events), traffic_finished_at,
        predicate=lambda event: set(expected_ips).issubset(
            str(user["id"]) for user in (event.get("users") or []))
    )

    assert heartbeat is not None, f"Both users were not reported in {len(candidates)} heartbeat(s)"
    reported_ips = {str(user["id"]): user["lastIpAddress"] for user in heartbeat["users"]}
    for user_id, expected_ip in expected_ips.items():
        actual_ip = reported_ips[user_id].removeprefix("::ffff:")
        assert actual_ip == expected_ip, f"User {user_id}: expected IP {expected_ip}, got {actual_ip}"


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
