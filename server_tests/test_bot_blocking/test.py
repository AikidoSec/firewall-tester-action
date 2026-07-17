from testlib import *
from core_api import CoreApi

'''
Tests bot blocking (blockedUserAgents) and bot monitoring (monitoredUserAgents).
A blocked user agent gets a 403. A monitored one passes through but still shows up
in heartbeat stats (userAgents.breakdown). Clearing blockedUserAgents at runtime
unblocks the bot; restoring it blocks the bot again.
'''

BLOCKED_BOT_UA = "Mozilla/5.0 BlockedTestBot/1.0"
MONITORED_BOT_UA = "Mozilla/5.0 MonitoredTestBot/1.0"
NORMAL_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NormalBrowser/1.0"


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    start_heartbeat_events = c.get_events("heartbeat")

    response = s.get("/api/pets/", headers={"User-Agent": BLOCKED_BOT_UA})
    collector.soft_assert_response_code_is(
        response, 403, f"Blocked bot should be blocked: {response.text}")
    collector.soft_assert_response_body_contains(
        response, "identified as a bot", f"Response should mention bot: {response.text}")

    response = s.get("/api/pets/", headers={"User-Agent": MONITORED_BOT_UA})
    collector.soft_assert_response_code_is(
        response, 200, f"Monitored bot should not be blocked: {response.text}")
    if response.status_code == 200:
        collector.soft_assert(isinstance(response.json(), list),
                              "Response body should be a list for monitored bot")

    response = s.get("/api/pets/", headers={"User-Agent": NORMAL_UA})
    collector.soft_assert_response_code_is(
        response, 200, f"Normal user agent should not be blocked: {response.text}")

    # First heartbeat lands ~30-60s after agent start
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

    heartbeat = new_heartbeat_events[0]
    breakdown = heartbeat.get("stats", {}).get("userAgents", {}).get("breakdown", {})
    collector.soft_assert(
        breakdown.get("blocked-test-bot") == 1,
        f"Expected 1 match for blocked-test-bot, got {breakdown.get('blocked-test-bot')} (breakdown: {breakdown})")
    collector.soft_assert(
        breakdown.get("monitored-test-bot") == 1,
        f"Expected 1 match for monitored-test-bot, got {breakdown.get('monitored-test-bot')} (breakdown: {breakdown})")
    collector.soft_assert(
        len(breakdown) == 2,
        f"Expected only the blocked and monitored bot keys in breakdown, got {breakdown}")

    c.update_runtime_firewall_file("change_config_remove_blocked_bot.json")

    response = s.get("/api/pets/", headers={"User-Agent": BLOCKED_BOT_UA})
    collector.soft_assert_response_code_is(
        response, 200, f"Bot should no longer be blocked after clearing blockedUserAgents: {response.text}")

    c.update_runtime_firewall_file("start_firewall.json")

    response = s.get("/api/pets/", headers={"User-Agent": BLOCKED_BOT_UA})
    collector.soft_assert_response_code_is(
        response, 403, f"Bot should be blocked again after restoring blockedUserAgents: {response.text}")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
