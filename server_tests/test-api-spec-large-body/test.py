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


def has_create_query_schema(route):
    return (
        route.get("method") == "POST"
        and route.get("path") == "/api/create"
        and route.get("apispec", {}).get("query")
    )


@with_heartbeats
def run_test(s: TestServer, c: CoreApi, collector, heartbeats):
    heartbeats.wait_for_next_interval()
    collector.raise_if_failures()
    response = s.post(*get_large_body_request())
    collector.soft_assert_response_code_is(response, 200, message="POST /api/create with a JSON body over 1 MiB")

    route = heartbeats.wait_for_entry("routes", has_create_query_schema)
    if not collector.soft_assert(route is not None, "Expected /api/create with a query schema in the heartbeat"):
        return

    apispec = route["apispec"]
    collector.soft_assert(
        "body" not in apispec or not apispec["body"],
        f"Expected no body schema for a body larger than 1 MiB, got: {apispec.get('body')}")
    collector.soft_assert(
        apispec.get("auth") == [{"type": "http", "scheme": "bearer"}],
        f"Expected auth info to still be reported, got: {apispec.get('auth')}")


if __name__ == "__main__":
    _, s, c = init_server_and_core()
    run_test(s, c)
