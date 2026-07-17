from testlib import *
from core_api import CoreApi

'''
Validates IP list matching across formats (single IPv4, IPv4 CIDR member, IPv4-mapped IPv6,
single IPv6, IPv6 CIDR member) in both blocking and monitoring mode, and that heartbeat stats
(ipAddresses.breakdown) reflect the matches in each mode:

1. With blockedIPAddresses populated (start_firewall.json): all 5 IP formats are blocked (403),
   a non-member control IP is allowed (200), and the heartbeat reports 5 matches.
2. After switching the same ranges to monitoredIPAddresses (change_config_monitor_mode.json):
   the same 5 IP formats now pass through (200) since monitoring never blocks, the control IP
   still passes, and the next heartbeat again reports 5 matches (this time from the monitored list).
'''

MATCHING_IPS = [
    {"ip": "93.184.216.34", "type": "single IPv4"},
    {"ip": "23.45.67.89", "type": "IPv4 CIDR member (23.45.67.0/24)"},
    {"ip": "::ffff:93.184.216.34", "type": "IPv4-mapped IPv6 of 93.184.216.34"},
    {"ip": "2606:2800:220:1:248:1893:25c8:1946", "type": "single IPv6"},
    {"ip": "2001:0db9:abcd:1234::5678", "type": "IPv6 CIDR member (2001:0db9:abcd:1234::/64)"},
]
CONTROL_IP = "1.2.3.4"


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    start_heartbeat_events = c.get_events("heartbeat")

    # 1. Blocking mode: all formats blocked, control IP allowed
    for entry in MATCHING_IPS:
        response = s.get("/api/pets/", headers={"X-Forwarded-For": entry["ip"]})
        collector.soft_assert_response_code_is(
            response, 403, f"{entry['type']} ({entry['ip']}) should be blocked: {response.text}")
        collector.soft_assert_response_body_contains(
            response, "is blocked", f"{entry['type']} ({entry['ip']}) response should indicate IP is blocked")

    response = s.get("/api/pets/", headers={"X-Forwarded-For": CONTROL_IP})
    collector.soft_assert_response_code_is(
        response, 200, f"Control IP {CONTROL_IP} should not be blocked: {response.text}")

    # Wait for the first heartbeat (sent ~30s after agent start) and inspect stats
    c.wait_for_new_events(
        70, old_events_length=len(start_heartbeat_events), filter_type="heartbeat"
    )
    all_heartbeat_events = c.get_events("heartbeat")
    new_heartbeat_events = all_heartbeat_events[len(start_heartbeat_events):]

    if not collector.soft_assert(
            len(new_heartbeat_events) == 1,
            f"Expected 1 heartbeat event, got {len(new_heartbeat_events)}"):
        collector.raise_if_failures()
        return

    blocked_breakdown = new_heartbeat_events[0].get(
        "stats", {}).get("ipAddresses", {}).get("breakdown", {})
    collector.soft_assert(
        blocked_breakdown.get("geoip/Belgium;BE") == len(MATCHING_IPS),
        f"Expected {len(MATCHING_IPS)} matches while blocking, got "
        f"{blocked_breakdown.get('geoip/Belgium;BE')} (breakdown: {blocked_breakdown})")

    # 2. Switch the same ranges to monitoring mode
    heartbeat_baseline_after_block_phase = len(all_heartbeat_events)
    c.update_runtime_firewall_file("change_config_monitor_mode.json")

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

    # Wait for the next heartbeat and inspect monitoring stats
    c.wait_for_new_events(
        150, old_events_length=heartbeat_baseline_after_block_phase, filter_type="heartbeat"
    )
    all_heartbeat_events = c.get_events("heartbeat")
    new_heartbeat_events = all_heartbeat_events[heartbeat_baseline_after_block_phase:]

    if not collector.soft_assert(
            len(new_heartbeat_events) >= 1,
            f"Expected at least 1 heartbeat event after switching to monitoring mode, got {len(new_heartbeat_events)}"):
        collector.raise_if_failures()
        return

    monitored_breakdown = new_heartbeat_events[-1].get(
        "stats", {}).get("ipAddresses", {}).get("breakdown", {})
    collector.soft_assert(
        monitored_breakdown.get("geoip/Belgium;BE") == len(MATCHING_IPS),
        f"Expected {len(MATCHING_IPS)} matches while monitoring, got "
        f"{monitored_breakdown.get('geoip/Belgium;BE')} (breakdown: {monitored_breakdown})")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
