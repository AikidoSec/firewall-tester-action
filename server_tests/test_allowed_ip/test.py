from testlib import *
from core_api import CoreApi

'''
Validate allowedIPAddresses supports single IPs, CIDR ranges, IPv4-mapped IPv6, and IPv6 (single + CIDR).

Steps:
1) With start_config (allowlist present):
   - Non-allowed IP is blocked.
   - Single IPv4, IPv4 CIDR member, IPv4-mapped IPv6, single IPv6, and IPv6 CIDR member are allowed.
2) Remove allowlist (change_config_remove_allowed_ip): previously blocked IP passes.
3) Restore allowlist (start_config): non-allowed IP is blocked again.
'''


def run_test(s: TestServer, c: CoreApi):
    # Baseline: start_config.json applied by runner
    non_allowed_ip = "1.3.3.7"
    ipv4_single = "185.245.255.212"
    ipv4_cidr_member = "185.245.255.55"          # in 185.245.255.0/24
    ipv4_mapped = "::ffff:185.245.255.212"       # explicit allowed entry
    ipv6_single = "2606:2800:220:1:248:1893:25c8:1946"
    ipv6_cidr_member = "2001:0db9:abcd:1234::abcd"

    # 1) With allowlist: non-allowed blocked
    response = s.get("/api/pets/", headers={"X-Forwarded-For": non_allowed_ip})
    assert_response_body_contains(response, "not allowed")
    assert_response_code_is(response, 403)

    # 1a) allowed entries are permitted
    for allowed_ip in [ipv4_single, ipv4_cidr_member, ipv4_mapped, ipv6_single, ipv6_cidr_member]:
        resp = s.get("/api/pets/", headers={"X-Forwarded-For": allowed_ip})
        assert_response_code_is(resp, 200)
        assert isinstance(resp.json(), list)

    # 2) Remove allowlist: previously blocked IP should pass
    c.update_runtime_config_file("change_config_remove_allowed_ip.json")
    response = s.get("/api/pets/", headers={"X-Forwarded-For": non_allowed_ip})
    assert_response_code_is(response, 200)
    assert isinstance(response.json(), list)

    # 3) Restore allowlist: non-allowed blocked again
    c.update_runtime_config_file("start_config.json")
    response = s.get("/api/pets/", headers={"X-Forwarded-For": non_allowed_ip})
    assert_response_code_is(response, 403)
    assert_response_body_contains(response, "not allowed")


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
