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


@with_heartbeats
def run_test(s: TestServer, c: CoreApi, collector, heartbeats):
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

    heartbeats.wait_for_counts("requests", "total", 2, since_startup=True)
    discovered = {route["path"] for route in heartbeats.entries("routes", since_startup=True)}
    for path in ("/api/create", "/api/pets"):
        collector.soft_assert(
            path in discovered,
            f"Excluded route {path} should still be discovered, found {sorted(discovered)}",
        )


if __name__ == "__main__":
    _, s, c = init_server_and_core()
    run_test(s, c)
