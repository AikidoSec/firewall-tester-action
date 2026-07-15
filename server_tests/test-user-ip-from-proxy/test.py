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

    c.wait_for_new_events(70, old_events_length=len(
        start_events), filter_type="heartbeat")

    all_events = c.get_events("heartbeat")
    new_events = all_events[len(start_events):]

    if not collector.soft_assert(len(new_events) >= 1, f"Expected at least 1 heartbeat event, got {len(new_events)}"):
        collector.raise_if_failures()
        return

    heartbeat = new_events[0]
    users = heartbeat.get("users", [])

    if not collector.soft_assert(len(users) >= 1, f"Expected at least 1 user in heartbeat, got {len(users)}"):
        collector.raise_if_failures()
        return

    target_user = None
    for user in users:
        if str(user.get("id")) == USER_ID:
            target_user = user
            break

    if not collector.soft_assert(target_user is not None, f"User {USER_ID} not found in heartbeat users: {users}"):
        collector.raise_if_failures()
        return

    last_ip = target_user.get("lastIpAddress", "")

    collector.soft_assert(
        last_ip == REAL_CLIENT_IP,
        f"User lastIpAddress should be '{REAL_CLIENT_IP}' (from X-Real-IP header), "
        f"but got '{last_ip}' (likely the Docker bridge/proxy IP)")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
