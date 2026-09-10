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
    ipv4_single = "185.245.255.212"
    ipv4_cidr_member = "185.245.255.55"          # in 185.245.255.0/24
    ipv4_mapped = "::ffff:185.245.255.212"       # explicit allowed entry
    ipv6_single = "2606:2800:220:1:248:1893:25c8:1946"
    ipv6_cidr_member = "2001:0db9:abcd:1234::abcd"
    ipv6_zoned = "fe80::1%eth0"                  # zone stripped vs. the unzoned allowlist entry
    ipv6_zoned_other = "fe80::1%wlan0"           # different zone, still stripped to a match
    ipv6_unzoned_vs_zoned_entry = "fe80::2"      # unzoned request vs. the zoned allowlist entry
    ipv6_other_zone_vs_zoned_entry = "fe80::2%wlan0"  # zone differs from the allowlist entry's

    # 1) With allowlist: non-allowed blocked
    response = s.get("/api/pets/", headers={"X-Forwarded-For": non_allowed_ip})
    collector.soft_assert_response_body_contains(response, "not allowed")
    collector.soft_assert_response_code_is(response, 403)

    # 1a) allowed entries are permitted
    for allowed_ip in [ipv4_single, ipv4_cidr_member, ipv4_mapped, ipv6_single, ipv6_cidr_member,
                        ipv6_zoned, ipv6_zoned_other,
                        ipv6_unzoned_vs_zoned_entry, ipv6_other_zone_vs_zoned_entry]:
        resp = s.get("/api/pets/", headers={"X-Forwarded-For": allowed_ip})
        collector.soft_assert_response_code_is(resp, 200)
        if resp.status_code == 200:
            collector.soft_assert(isinstance(resp.json(), list), f"Response body should be a list for allowed IP {allowed_ip}")

    # 1b) a different host on the same link-local prefix is still blocked
    response = s.get("/api/pets/", headers={"X-Forwarded-For": "fe80::3"})
    collector.soft_assert_response_body_contains(response, "not allowed")
    collector.soft_assert_response_code_is(response, 403)

    # 2) Remove allowlist: previously blocked IP should pass
    c.update_runtime_config_file("change_config_remove_allowed_ip.json")
    response = s.get("/api/pets/", headers={"X-Forwarded-For": non_allowed_ip})
    collector.soft_assert_response_code_is(response, 200)
    if response.status_code == 200:
        collector.soft_assert(isinstance(response.json(), list), "Response body should be a list after removing allowlist")

    # 3) Restore allowlist: non-allowed blocked again
    c.update_runtime_config_file("start_config.json")
    response = s.get("/api/pets/", headers={"X-Forwarded-For": non_allowed_ip})
    collector.soft_assert_response_code_is(response, 403)
    collector.soft_assert_response_body_contains(response, "not allowed")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
