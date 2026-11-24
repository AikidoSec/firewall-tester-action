import time
from socket import gethostname, gethostbyname
from testlib import *
from core_api import CoreApi

'''
Tests that when AIKIDO_TRUST_PROXY=true and AIKIDO_CLIENT_IP_HEADER=X-Real-IP,
the user's lastIpAddress in heartbeat events reflects the resolved client IP
from the proxy header — not the raw TCP connection IP (e.g. Docker bridge).

1. Send requests with a user header and X-Real-IP proxy header.
2. Wait for a heartbeat event.
3. Verify the user's lastIpAddress matches X-Real-IP, not the container IP.
4. Verify a request without X-Real-IP reports the runner's container IP.
   The runner and app are separate containers, so the runner is the client.
'''

REAL_CLIENT_IP = "11.22.33.44"
USER_ID = "42"
USER_ID_WITHOUT_PROXY_HEADER = "43"


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    heartbeats = c.track_heartbeats(collector)

    for _ in range(3):
        response = s.get("/api/pets/", headers={
            "user": USER_ID,
            "X-Real-IP": REAL_CLIENT_IP
        })
        collector.soft_assert_response_code_is(response, 200)
        time.sleep(0.5)

    response = s.get("/api/pets/", headers={"user": USER_ID_WITHOUT_PROXY_HEADER})
    collector.soft_assert_response_code_is(response, 200)

    users = heartbeats.wait_for_entries(
        {USER_ID, USER_ID_WITHOUT_PROXY_HEADER}, field="users", key=lambda user: str(user.get("id")))
    collector.raise_if_failures()

    target_user = next(user for user in users if str(user.get("id")) == USER_ID)
    last_ip = target_user.get("lastIpAddress", "")
    collector.soft_assert(
        last_ip == REAL_CLIENT_IP,
        f"User lastIpAddress should be '{REAL_CLIENT_IP}' (from X-Real-IP header), "
        f"but got '{last_ip}' (likely the Docker bridge/proxy IP)")

    user_without_proxy = next(user for user in users
                              if str(user.get("id")) == USER_ID_WITHOUT_PROXY_HEADER)
    expected_ip = gethostbyname(gethostname())
    actual_ip = user_without_proxy.get("lastIpAddress", "").removeprefix("::ffff:")
    collector.soft_assert(
        actual_ip == expected_ip,
        f"User {USER_ID_WITHOUT_PROXY_HEADER} lastIpAddress should be '{expected_ip}' "
        f"(the test runner's IP), but got '{actual_ip}'")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
