from testlib import *
from core_api import CoreApi

"""
Routes with forceProtectionOff do not count towards the reported statistics

This test verifies that:
1. Requests to routes with protection disabled are not blocked, even when they contain attacks
2. Requests to routes with protection disabled are not counted in `stats.requests.total`
3. Requests to routes with protection disabled do not generate API spec discovery data (routes in heartbeat)
4. Requests to routes with protection disabled do not count towards attack statistics
5. Requests to a route with protection enabled are still counted
"""


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    start_heartbeat_events = c.get_events("heartbeat")

    for _ in range(3):
        response = s.post("/api/create", {"name": "test2", "age": 34})
        collector.soft_assert_response_code_is(
            response, 200, "POST /api/create (protection off)"
        )
    response = s.post(
        "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"}
    )
    collector.soft_assert_response_code_is(
        response, 200, "sql injection on route with protection off"
    )
    response = s.get("/api/read?path=../secrets/key.txt")
    collector.soft_assert_response_code_is(
        response, 200, "path traversal on route with protection off"
    )

    response = s.get("/api/pets/")
    collector.soft_assert_response_code_is(response, 200, "GET /api/pets")

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
        f"Only the initial request and the control request should be counted, found {requests_total}",
    )

    for event in all_heartbeat_events:
        for route in event.get("routes", []):
            collector.soft_assert(
                route["path"] not in ("/api/create", "/api/read"),
                f"Heartbeat should not contain routes with protection off: {route}",
            )

    collector.soft_assert(
        heartbeat["stats"]["requests"]["attacksDetected"]["total"] == 0,
        f"Attacks detected should be 0, found {heartbeat['stats']['requests']['attacksDetected']['total']}",
    )

    collector.raise_if_failures()


if __name__ == "__main__":
    _, s, c = init_server_and_core()
    run_test(s, c)
