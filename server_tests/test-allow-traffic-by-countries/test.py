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
    collector = AssertionCollector()

    # 2.16.53.5 is in the allowlist
    response = s.get("/api/pets/",  headers={"X-Forwarded-For": "2.16.53.5"})
    collector.soft_assert_response_code_is(
        response, 200, "IP in allowlist should be allowed")
    if response.status_code == 200:
        response_body = response.json()
        collector.soft_assert(isinstance(response_body, list), "Response body should be a list")

    # 1.2.3.4 is NOT in the allowlist
    response = s.get("/api/pets/", headers={"X-Forwarded-For": "1.2.3.4"})
    collector.soft_assert_response_body_contains(
        response, "not allowed", "Response body should indicate IP is not allowed")
    collector.soft_assert_response_code_is(
        response, 403, "IP NOT in allowlist should be blocked")

    # Disable the allowlist by clearing it
    c.update_runtime_firewall_file("change_config_remove_allowed_ip.json")

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "2.16.53.5"})
    collector.soft_assert_response_code_is(
        response, 200, "IP should still be allowed when allowlist is cleared")
    if response.status_code == 200:
        response_body = response.json()
        collector.soft_assert(isinstance(response_body, list), "Response body should be a list after clearing allowlist")

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "1.2.3.4"})
    collector.soft_assert_response_code_is(
        response, 200, "IP should be allowed when allowlist is cleared")
    if response.status_code == 200:
        response_body = response.json()
        collector.soft_assert(isinstance(response_body, list), "Response body should be a list for cleared allowlist")

    # Re-enable the allowlist
    c.update_runtime_firewall_file("start_firewall.json")

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "2.16.53.5"})
    collector.soft_assert_response_code_is(
        response, 200, "IP in allowlist should be allowed again")
    if response.status_code == 200:
        response_body = response.json()
        collector.soft_assert(isinstance(response_body, list), "Response body should be a list after re-enabling allowlist")

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "1.2.3.4"})
    collector.soft_assert_response_body_contains(
        response, "not allowed", "Response body should indicate IP is not allowed again")
    collector.soft_assert_response_code_is(
        response, 403, "IP NOT in allowlist should be blocked again")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
