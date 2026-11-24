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
    heartbeats = c.track_heartbeats(collector)

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

    heartbeats.wait_for_request_count(2)
    for route in heartbeats.entries("routes", include_startup=True):
        collector.soft_assert(
            route["path"] not in ("/api/create", "/api/read"),
            f"Heartbeat should not contain routes with protection off: {route}",
        )

    attacks = heartbeats.attacks_detected()
    collector.soft_assert(attacks == 0, f"Attacks detected should be 0, found {attacks}")

    collector.raise_if_failures()


if __name__ == "__main__":
    _, s, c = init_server_and_core()
    run_test(s, c)
