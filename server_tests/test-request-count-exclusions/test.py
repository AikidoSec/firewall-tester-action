from testlib import *
from core_api import CoreApi

"""
Routes matching requestCountExclusions are not counted in the total request count

Config: exact ["/api/create"], suffix ["", "/pets"] (empty suffix must be skipped)

This test verifies that:
1. Requests to a route matching `exact` (/api/create) are not counted in `stats.requests.total`
2. Requests to a route matching `suffix` (/api/pets) are not counted, also not when rate limited
3. Excluded routes are still discovered and show up in the heartbeat routes
4. Requests to other routes (/) are still counted, so the empty suffix does not match everything
"""


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    start_heartbeat_events = c.get_events("heartbeat")

    for _ in range(3):
        response = s.post("/api/create", {"name": "test2", "age": 34})
        collector.soft_assert_response_code_is(
            response, 200, "POST /api/create (exact exclusion)"
        )

    codes = [s.get("/api/pets/").status_code for _ in range(5)]
    collector.soft_assert(
        codes[:2] == [200, 200] and all(code == 429 for code in codes[2:]),
        f"Expected 2 successful and 3 rate limited requests on /api/pets, got {codes}",
    )

    response = s.get("/")
    collector.soft_assert_response_code_is(response, 200, "GET / (counted)")

    traffic_finished_at = int(time.time() * 1000)
    heartbeat, candidates = c.wait_for_heartbeat_after(
        160, len(start_heartbeat_events), traffic_finished_at
    )
    all_heartbeat_events = c.get_events("heartbeat")
    if not collector.soft_assert(
        heartbeat is not None,
        f"Expected a heartbeat produced after test traffic, got {len(candidates)} candidate heartbeat(s)",
    ):
        collector.raise_if_failures()
        return

    requests_total = sum(
        event.get("stats", {}).get("requests", {}).get("total", 0)
        for event in all_heartbeat_events
    )
    collector.soft_assert(
        requests_total == 2,
        f"Only the initial request and the control request to / should be counted, found {requests_total}",
    )

    discovered = {
        route["path"]
        for event in all_heartbeat_events
        for route in event.get("routes", [])
    }
    for path in ("/api/create", "/api/pets"):
        collector.soft_assert(
            path in discovered,
            f"Excluded route {path} should still be discovered, found {sorted(discovered)}",
        )

    collector.raise_if_failures()


if __name__ == "__main__":
    _, s, c = init_server_and_core()
    run_test(s, c)
