from testlib import *
from core_api import CoreApi

'''
Tests the traffic allowance by countries (allowlist) feature:

1. Tests that IPs in the allowlist are allowed.
2. Tests that IPs NOT in the allowlist are blocked.
3. Tests that when the allowlist is empty, all IPs are allowed.
4. Tests that bypassed IPs (allowedIPAddresses in start_config.json) are always allowed.
5. Tests runtime updates of the allowlist configuration.
'''


def run_test(s: TestServer, c: CoreApi):
    # 2.16.53.5 is in the allowlist
    response = s.get("/api/pets/",  headers={"X-Forwarded-For": "2.16.53.5"})
    assert_response_code_is(
        response, 200, "IP in allowlist should be allowed")
    response_body = response.json()
    assert isinstance(response_body, list)

    # 1.2.3.4 is NOT in the allowlist
    response = s.get("/api/pets/", headers={"X-Forwarded-For": "1.2.3.4"})
    assert_response_body_contains(
        response, "not allowed", "Response body should indicate IP is not allowed")
    assert_response_code_is(
        response, 403, "IP NOT in allowlist should be blocked")

    # Disable the allowlist by clearing it
    c.update_runtime_firewall_file("change_config_remove_allowed_ip.json")

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "2.16.53.5"})
    assert_response_code_is(
        response, 200, "IP should still be allowed when allowlist is cleared")
    response_body = response.json()
    assert isinstance(response_body, list)

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "1.2.3.4"})
    assert_response_code_is(
        response, 200, "IP should be allowed when allowlist is cleared")
    response_body = response.json()
    assert isinstance(response_body, list)

    # Re-enable the allowlist
    c.update_runtime_firewall_file("start_firewall.json")

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "2.16.53.5"})
    assert_response_code_is(
        response, 200, "IP in allowlist should be allowed again")
    response_body = response.json()
    assert isinstance(response_body, list)

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "1.2.3.4"})
    assert_response_body_contains(
        response, "not allowed", "Response body should indicate IP is not allowed again")
    assert_response_code_is(
        response, 403, "IP NOT in allowlist should be blocked again")


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
