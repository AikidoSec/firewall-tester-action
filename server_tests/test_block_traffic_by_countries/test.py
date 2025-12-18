from testlib import *
from core_api import CoreApi

'''
Tests the traffic blocking by countries (blocklist) feature:

1. Tests that IPs in the blocklist are blocked.
2. Tests that IPs NOT in the blocklist are allowed.
3. Tests that when the blocklist is empty, all IPs are allowed.
4. Tests that bypassed IPs (allowedIPAddresses in start_config.json) are always allowed even if they are in the blocklist.
5. Tests runtime updates of the blocklist configuration.
'''


def run_test(s: TestServer, c: CoreApi):
    # 2.16.53.5 is in the blocklist
    response = s.get("/api/pets/",  headers={"X-Forwarded-For": "2.16.53.5"})
    assert_response_body_contains(
        response, "is blocked", "Response body should indicate IP is blocked")
    assert_response_code_is(response, 403, "IP in blocklist should be blocked")

    # 2.16.53.6 is configured as a bypassed IP in start_config.json
    response = s.get("/api/pets/",  headers={"X-Forwarded-For": "2.16.53.6"})
    assert_response_code_is(response, 200, "bypassed IP should be allowed")
    response_body = response.json()
    assert isinstance(response_body, list)

    # 1.2.3.4 is NOT in the blocklist
    response = s.get("/api/pets/", headers={"X-Forwarded-For": "1.2.3.4"})
    assert_response_code_is(
        response, 200, "IP NOT in blocklist should be allowed")
    response_body = response.json()
    assert isinstance(response_body, list)

    # Disable the blocklist by clearing it
    c.update_runtime_firewall_file("change_config_remove_blocked_ips.json")

    response = s.get("/api/pets/",  headers={"X-Forwarded-For": "2.16.53.5"})
    assert_response_code_is(
        response, 200, "IP should be allowed when blocklist is cleared")
    response_body = response.json()
    assert isinstance(response_body, list)

    response = s.get("/api/pets/",  headers={"X-Forwarded-For": "2.16.53.6"})
    assert_response_code_is(
        response, 200, "bypassed IP should still be allowed when blocklist is cleared")
    response_body = response.json()
    assert isinstance(response_body, list)

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "1.2.3.4"})
    assert_response_code_is(
        response, 200, "IP should still be allowed when blocklist is cleared")
    response_body = response.json()
    assert isinstance(response_body, list)

    # Re-enable the blocklist
    c.update_runtime_firewall_file("start_firewall.json")

    response = s.get("/api/pets/",  headers={"X-Forwarded-For": "2.16.53.5"})
    assert_response_body_contains(
        response, "is blocked", "Response body should indicate IP is blocked again")
    assert_response_code_is(
        response, 403, "IP in blocklist should be blocked again")

    response = s.get("/api/pets/",  headers={"X-Forwarded-For": "2.16.53.6"})
    assert_response_code_is(
        response, 200, "bypassed IP should still be allowed again")
    response_body = response.json()
    assert isinstance(response_body, list)

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "1.2.3.4"})
    assert_response_code_is(
        response, 200, "IP NOT in blocklist should still be allowed")
    response_body = response.json()
    assert isinstance(response_body, list)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
