import time
from testlib import *
from core_api import CoreApi


'''
1. Sets up a simple config.
2. Sends one JSON post request with a body larger than 1 MiB (and a query string).
3. Waits for the heartbeat event and validates that the API schema reporting
   skipped the body schema, but still reported the query schema and auth type.
'''

MAX_BODY_SIZE_BYTES = 1024 * 1024


def get_large_body_request():
    url = "/api/create?userId=12345"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer your_token_here"
    }
    body = {
        # Keep "name" short: the demo apps store it in the DB, and an oversized
        # value would make the app respond with 500 (no API spec is collected then).
        "name": "large-body-test",
        "padding": "a" * (MAX_BODY_SIZE_BYTES + 1024),
        "age": 34
    }
    return url, body, headers


def find_route(heartbeat, method, path):
    for route in heartbeat.get("routes", []):
        if route.get("method") == method and route.get("path") == path:
            return route
    return None


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    start_events = c.get_events("heartbeat")
    if not collector.soft_assert(
            c.wait_for_new_events(160, len(start_events), "heartbeat"),
            "Expected a fresh heartbeat before sending the large body request"):
        collector.raise_if_failures()
        return
    start_events = c.get_events("heartbeat")

    response = s.post(*get_large_body_request())
    collector.soft_assert_response_code_is(response, 200)

    traffic_finished_at = int(time.time() * 1000)
    last_error = None

    def has_route_with_query_spec(heartbeat):
        nonlocal last_error
        route = find_route(heartbeat, "POST", "/api/create")
        if route is None or not route.get("apispec", {}).get("query"):
            last_error = "Expected /api/create with a query schema in the heartbeat"
            return False
        return True

    heartbeat, candidates = c.wait_for_heartbeat_after(
        160, len(start_events), traffic_finished_at,
        predicate=has_route_with_query_spec
    )

    if not collector.soft_assert(
            heartbeat is not None,
            last_error or
            f"Expected a heartbeat produced after test traffic, got {len(candidates)} candidate heartbeat(s)"):
        collector.raise_if_failures()
        return

    route = find_route(heartbeat, "POST", "/api/create")
    apispec = route["apispec"]
    collector.soft_assert(
        "body" not in apispec or not apispec["body"],
        f"Expected no body schema for a body larger than 1 MiB, got: {apispec.get('body')}")
    collector.soft_assert(
        apispec.get("auth") == [{"type": "http", "scheme": "bearer"}],
        f"Expected auth info to still be reported, got: {apispec.get('auth')}")

    collector.raise_if_failures()


if __name__ == "__main__":
    _, s, c = init_server_and_core()
    run_test(s, c)
