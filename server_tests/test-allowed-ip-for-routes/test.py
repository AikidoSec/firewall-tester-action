from testlib import *
from core_api import CoreApi

'''
Validate allowedIPAddresses supports single IPs, CIDR ranges, IPv4-mapped IPv6, and IPv6 (single + CIDR).

Steps:
1) With start_config (allowlist present):
   - Non-allowed IP is blocked.
   - Single IPv4, IPv4 CIDR member, IPv4-mapped IPv6, single IPv6, and IPv6 CIDR member are allowed.
   - The zone is stripped on both sides: an unzoned allowlist entry matches a zoned request
     address, and a zoned allowlist entry matches an unzoned (or differently-zoned) request.
2) Remove allowlist (change_config_remove_allowed_ip): previously blocked IP passes.
3) Restore allowlist (start_config): non-allowed IP is blocked again.
'''


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    # Baseline: start_config.json applied by runner
    non_allowed_ip = "1.3.3.7"

    # 1) With allowlist: non-allowed blocked
    response = s.get("/api/pets/", headers={"X-Forwarded-For": non_allowed_ip})
    message = f"Client {non_allowed_ip} outside the initial allowlist"
    collector.soft_assert_response_body_contains(response, "not allowed", message=message)
    collector.soft_assert_response_code_is(response, 403, message=message)

    # 1a) allowed entries are permitted
    for client_ip, allowlist_entry in [
        ("185.245.255.212", "185.245.255.212"),
        ("185.245.255.55", "185.245.255.0/24"),
        ("::ffff:185.245.255.212", "::ffff:185.245.255.212"),
        ("2606:2800:220:1:248:1893:25c8:1946", "2606:2800:220:1:248:1893:25c8:1946"),
        ("2001:0db9:abcd:1234::abcd", "2001:0db9:abcd:1234::/64"),
        ("fe80::1%eth0", "fe80::1"),
        ("fe80::1%wlan0", "fe80::1"),
        ("fe80::2", "fe80::2%eth0"),
        ("fe80::2%wlan0", "fe80::2%eth0"),
    ]:
        resp = s.get("/api/pets/", headers={"X-Forwarded-For": client_ip})
        message = f"Client {client_ip} should match allowlist entry {allowlist_entry}"
        if "%" in client_ip or "%" in allowlist_entry:
            message += " after ignoring the IPv6 zone ID"
        collector.soft_assert_response_code_is(resp, 200, message=message)
        if resp.status_code == 200:
            collector.soft_assert(isinstance(resp.json(), list), f"Response body should be a list for allowed IP {client_ip}")

    # 1b) a different host on the same link-local prefix is still blocked
    response = s.get("/api/pets/", headers={"X-Forwarded-For": "fe80::3"})
    message = "Client fe80::3 is outside the allowlist"
    collector.soft_assert_response_body_contains(response, "not allowed", message=message)
    collector.soft_assert_response_code_is(response, 403, message=message)

    # 2) Remove allowlist: previously blocked IP should pass
    c.update_runtime_config_file("change_config_remove_allowed_ip.json")
    response = s.get("/api/pets/", headers={"X-Forwarded-For": non_allowed_ip})
    collector.soft_assert_response_code_is(
        response, 200, message=f"Client {non_allowed_ip} after removing the allowlist"
    )
    if response.status_code == 200:
        collector.soft_assert(isinstance(response.json(), list), "Response body should be a list after removing allowlist")

    # 3) Restore allowlist: non-allowed blocked again
    c.update_runtime_config_file("start_config.json")
    response = s.get("/api/pets/", headers={"X-Forwarded-For": non_allowed_ip})
    message = f"Client {non_allowed_ip} after restoring the allowlist"
    collector.soft_assert_response_code_is(response, 403, message=message)
    collector.soft_assert_response_body_contains(response, "not allowed", message=message)

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
