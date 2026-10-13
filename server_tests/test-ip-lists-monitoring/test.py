import time
from testlib import *
from core_api import CoreApi

'''
Tests IP list matching across formats (single IPv4, IPv4 CIDR member, IPv4-mapped IPv6,
single IPv6, IPv6 CIDR member) in both blocking and monitoring mode, and checks that
heartbeat stats (ipAddresses.breakdown) reflect the matches in each mode.
'''

MATCHING_IPS = [
    {"ip": "93.184.216.34", "type": "single IPv4"},
    {"ip": "23.45.67.89", "type": "IPv4 CIDR member (23.45.67.0/24)"},
    {"ip": "::ffff:93.184.216.34", "type": "IPv4-mapped IPv6 of 93.184.216.34"},
    {"ip": "2606:2800:220:1:248:1893:25c8:1946", "type": "single IPv6"},
    {"ip": "2001:0db9:abcd:1234::5678", "type": "IPv6 CIDR member (2001:0db9:abcd:1234::/64)"},
]
CONTROL_IP = "1.2.3.4"
IP_LIST_KEY = "geoip/Belgium;BE"


def check_ip_list_matches(collector, c: CoreApi, heartbeat_count_before_traffic, traffic_finished_at, mode):
    heartbeat, candidates = c.wait_for_heartbeat_after(
        160, heartbeat_count_before_traffic, traffic_finished_at
    )

    if not collector.soft_assert(
            heartbeat is not None,
            f"Expected a heartbeat produced after the {mode} traffic, got {len(candidates)} candidate heartbeat(s)"):
        return

    breakdown = heartbeat.get("stats", {}).get("ipAddresses", {}).get("breakdown", {})
    collector.soft_assert(
        breakdown.get(IP_LIST_KEY) == len(MATCHING_IPS),
        f"Expected {len(MATCHING_IPS)} matches while {mode}, got "
        f"{breakdown.get(IP_LIST_KEY)} (breakdown: {breakdown})")


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    heartbeat_count_before_traffic = len(c.get_events("heartbeat"))

    for entry in MATCHING_IPS:
        response = s.get("/api/pets/", headers={"X-Forwarded-For": entry["ip"]})
        collector.soft_assert_response_code_is(
            response, 403, f"{entry['type']} ({entry['ip']}) should be blocked: {response.text}")
        collector.soft_assert_response_body_contains(
            response, "is blocked", f"{entry['type']} ({entry['ip']}) response should indicate IP is blocked")

    response = s.get("/api/pets/", headers={"X-Forwarded-For": CONTROL_IP})
    collector.soft_assert_response_code_is(
        response, 200, f"Control IP {CONTROL_IP} should not be blocked: {response.text}")

    check_ip_list_matches(
        collector, c, heartbeat_count_before_traffic, int(time.time() * 1000), "blocking")

    c.update_runtime_firewall_file("change_config_monitor_mode.json")
    heartbeat_count_before_traffic = len(c.get_events("heartbeat"))

    for entry in MATCHING_IPS:
        response = s.get("/api/pets/", headers={"X-Forwarded-For": entry["ip"]})
        collector.soft_assert_response_code_is(
            response, 200, f"{entry['type']} ({entry['ip']}) should not be blocked while monitored: {response.text}")
        if response.status_code == 200:
            collector.soft_assert(isinstance(response.json(), list),
                                  f"Response body should be a list for monitored IP {entry['ip']}")

    response = s.get("/api/pets/", headers={"X-Forwarded-For": CONTROL_IP})
    collector.soft_assert_response_code_is(
        response, 200, f"Control IP {CONTROL_IP} should still not be blocked: {response.text}")

    check_ip_list_matches(
        collector, c, heartbeat_count_before_traffic, int(time.time() * 1000), "monitoring")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
