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
    collector = AssertionCollector()

    # 2.16.53.5 is in the blocklist
    response = s.get("/api/pets/",  headers={"X-Forwarded-For": "2.16.53.5"})
    collector.soft_assert_response_body_contains(
        response, "is blocked", "Response body should indicate IP is blocked")
    collector.soft_assert_response_code_is(response, 403, "IP in blocklist should be blocked")

    # 2.16.53.6 is configured as a bypassed IP in start_config.json
    response = s.get("/api/pets/",  headers={"X-Forwarded-For": "2.16.53.6"})
    collector.soft_assert_response_code_is(response, 200, "bypassed IP should be allowed")
    if response.status_code == 200:
        response_body = response.json()
        collector.soft_assert(isinstance(response_body, list), "Response body should be a list for bypassed IP")

    # 1.2.3.4 is NOT in the blocklist
    response = s.get("/api/pets/", headers={"X-Forwarded-For": "1.2.3.4"})
    collector.soft_assert_response_code_is(
        response, 200, "IP NOT in blocklist should be allowed")
    if response.status_code == 200:
        response_body = response.json()
        collector.soft_assert(isinstance(response_body, list), "Response body should be a list for non-blocked IP")

    # Disable the blocklist by clearing it
    c.update_runtime_firewall_file("change_config_remove_blocked_ips.json")

    response = s.get("/api/pets/",  headers={"X-Forwarded-For": "2.16.53.5"})
    collector.soft_assert_response_code_is(
        response, 200, "IP should be allowed when blocklist is cleared")
    if response.status_code == 200:
        response_body = response.json()
        collector.soft_assert(isinstance(response_body, list), "Response body should be a list when blocklist cleared")

    response = s.get("/api/pets/",  headers={"X-Forwarded-For": "2.16.53.6"})
    collector.soft_assert_response_code_is(
        response, 200, "bypassed IP should still be allowed when blocklist is cleared")
    if response.status_code == 200:
        response_body = response.json()
        collector.soft_assert(isinstance(response_body, list), "Response body should be a list for bypassed IP cleared blocklist")

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "1.2.3.4"})
    collector.soft_assert_response_code_is(
        response, 200, "IP should still be allowed when blocklist is cleared")
    if response.status_code == 200:
        response_body = response.json()
        collector.soft_assert(isinstance(response_body, list), "Response body should be a list when blocklist cleared for 1.2.3.4")

    # Re-enable the blocklist
    c.update_runtime_firewall_file("start_firewall.json")

    response = s.get("/api/pets/",  headers={"X-Forwarded-For": "2.16.53.5"})
    collector.soft_assert_response_body_contains(
        response, "is blocked", "Response body should indicate IP is blocked again")
    collector.soft_assert_response_code_is(
        response, 403, "IP in blocklist should be blocked again")

    response = s.get("/api/pets/",  headers={"X-Forwarded-For": "2.16.53.6"})
    collector.soft_assert_response_code_is(
        response, 200, "bypassed IP should still be allowed again")
    if response.status_code == 200:
        response_body = response.json()
        collector.soft_assert(isinstance(response_body, list), "Response body should be a list for bypassed IP re-enabled blocklist")

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "1.2.3.4"})
    collector.soft_assert_response_code_is(
        response, 200, "IP NOT in blocklist should still be allowed")
    if response.status_code == 200:
        response_body = response.json()
        collector.soft_assert(isinstance(response_body, list), "Response body should be a list for non-blocked IP re-enabled")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
