from testlib import *
from core_api import CoreApi

'''
Validates bot blocking (blockedUserAgents) and bot monitoring (monitoredUserAgents):

1. A request with a blocked user agent is blocked (403) and identified as a bot.
2. A request with a monitored (but not blocked) user agent passes through (200).
3. A request with a normal user agent passes through (200) and is not counted in bot stats.
4. Heartbeat stats (userAgents.breakdown) report exactly 1 match for the blocked bot key
   and 1 match for the monitored bot key, with no entry for the normal user agent.
5. Removing blockedUserAgents at runtime lets the previously blocked bot through;
   restoring it blocks the bot again.
'''

BLOCKED_BOT_UA = "Mozilla/5.0 BlockedTestBot/1.0"
MONITORED_BOT_UA = "Mozilla/5.0 MonitoredTestBot/1.0"
NORMAL_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NormalBrowser/1.0"


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    start_heartbeat_events = c.get_events("heartbeat")

    # 1. Blocked user agent should be blocked
    response = s.get("/api/pets/", headers={"User-Agent": BLOCKED_BOT_UA})
    collector.soft_assert_response_code_is(
        response, 403, f"Blocked bot should be blocked: {response.text}")
    collector.soft_assert_response_body_contains(
        response, "identified as a bot", f"Response should mention bot: {response.text}")

    # 2. Monitored user agent should pass through (monitor mode never blocks)
    response = s.get("/api/pets/", headers={"User-Agent": MONITORED_BOT_UA})
    collector.soft_assert_response_code_is(
        response, 200, f"Monitored bot should not be blocked: {response.text}")
    if response.status_code == 200:
        collector.soft_assert(isinstance(response.json(), list),
                              "Response body should be a list for monitored bot")

    # 3. Normal user agent should pass through and not be tracked as a bot match
    response = s.get("/api/pets/", headers={"User-Agent": NORMAL_UA})
    collector.soft_assert_response_code_is(
        response, 200, f"Normal user agent should not be blocked: {response.text}")

    # Wait for the first heartbeat (sent ~30s after agent start) and inspect bot stats
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

    # 4. Dynamic reload: clearing blockedUserAgents should let the bot through
    c.update_runtime_firewall_file("change_config_remove_blocked_bot.json")

    response = s.get("/api/pets/", headers={"User-Agent": BLOCKED_BOT_UA})
    collector.soft_assert_response_code_is(
        response, 200, f"Bot should no longer be blocked after clearing blockedUserAgents: {response.text}")

    # 5. Restoring blockedUserAgents should block the bot again
    c.update_runtime_firewall_file("start_firewall.json")

    response = s.get("/api/pets/", headers={"User-Agent": BLOCKED_BOT_UA})
    collector.soft_assert_response_code_is(
        response, 403, f"Bot should be blocked again after restoring blockedUserAgents: {response.text}")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
