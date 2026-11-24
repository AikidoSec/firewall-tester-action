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

    heartbeats = c.track_heartbeats(collector)

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

    heartbeats.wait_for_totals(
        "userAgents", "breakdown", {"blocked-test-bot": 1, "monitored-test-bot": 1}, allow_extra=False)

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
