import time

from core_api import CoreApi
from testlib import (
    AssertionCollector,
    TestServer,
    get_response_status_code,
    init_server_and_core,
)


MAX_EVENTS_PER_REQUEST = 25
CLIENT_IP = "11.22.33.44"
USER_AGENT = "firewall-tester-custom-event/1.0"


def get_successful_response(
    collector, s: TestServer, route: str, client_ip: str = CLIENT_IP
):
    response = s.get(
        route,
        headers={
            "User-Agent": USER_AGENT,
            "X-Forwarded-For": client_ip,
        },
    )
    status_code = get_response_status_code(response)
    collector.soft_assert(
        status_code is not None and 200 <= status_code < 300,
        f"Expected a successful response, got status {status_code}",
    )


def test_single_custom_event(collector, s: TestServer, c: CoreApi):
    route = "/api/custom-event"
    event_name = "user.login_failed"
    initial_count = len(c.get_events("custom"))
    request_started_at_ms = int(time.time() * 1000)

    get_successful_response(collector, s, route)

    c.wait_for_new_events(10, initial_count, "custom")
    new_events = c.get_events("custom")[initial_count:]
    matching_events = [event for event in new_events if event.get("name") == event_name]
    if not collector.soft_assert(
        len(matching_events) == 1,
        f"Expected one new {event_name} custom event, got {matching_events}",
    ):
        return

    event = matching_events[0]
    request = event.get("request")
    if collector.soft_assert(
        isinstance(request, dict),
        f"Expected request metadata to be an object, got {request!r}",
    ):
        collector.soft_assert(
            request.get("method") == "GET",
            f"Expected request method GET, got {request.get('method')!r}",
        )
        collector.soft_assert(
            request.get("ipAddress") == CLIENT_IP,
            f"Expected request IP {CLIENT_IP}, got {request.get('ipAddress')!r}",
        )
        collector.soft_assert(
            request.get("userAgent") == USER_AGENT,
            f"Expected user agent {USER_AGENT}, got {request.get('userAgent')!r}",
        )
        collector.soft_assert(
            request.get("route") == route,
            f"Expected request route {route}, got {request.get('route')!r}",
        )

    collector.soft_assert(
        event.get("type") == "custom",
        f"Expected event type custom, got {event.get('type')!r}",
    )
    event_time = event.get("time")
    collector.soft_assert(
        isinstance(event_time, int)
        and not isinstance(event_time, bool)
        and request_started_at_ms <= event_time <= int(time.time() * 1000),
        f"Expected an integer millisecond timestamp for the request, got {event_time!r}",
    )
    agent = event.get("agent")
    collector.soft_assert(
        isinstance(agent, dict) and len(agent) > 0,
        f"Expected non-empty agent metadata, got {agent!r}",
    )


def test_custom_event_limit(collector, s: TestServer, c: CoreApi):
    initial_count = len(c.get_events("custom"))

    get_successful_response(collector, s, "/api/custom-event-limit")

    c.wait_for_new_events(10, initial_count + MAX_EVENTS_PER_REQUEST - 1, "custom")
    c.wait_for_new_events(2, initial_count + MAX_EVENTS_PER_REQUEST, "custom")

    new_events = c.get_events("custom")[initial_count:]
    event_names = {event.get("name") for event in new_events}
    expected_names = {
        f"custom-event-{index}" for index in range(MAX_EVENTS_PER_REQUEST)
    }
    collector.soft_assert(
        len(new_events) == MAX_EVENTS_PER_REQUEST,
        f"Expected {MAX_EVENTS_PER_REQUEST} custom events, got {len(new_events)}",
    )
    collector.soft_assert(
        event_names == expected_names,
        f"Expected custom events {expected_names}, got {event_names}",
    )


def test_bypassed_custom_event(collector, s: TestServer, c: CoreApi):
    initial_count = len(c.get_events("custom"))

    get_successful_response(
        collector, s, "/api/custom-event", client_ip="93.184.216.34"
    )

    c.wait_for_new_events(2, initial_count, "custom")
    new_events = c.get_events("custom")[initial_count:]
    collector.soft_assert(
        len(new_events) == 0,
        f"Expected no custom event from a bypassed request, got {new_events}",
    )


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    test_single_custom_event(collector, s, c)
    test_custom_event_limit(collector, s, c)
    test_bypassed_custom_event(collector, s, c)

    collector.raise_if_failures()


if __name__ == "__main__":
    args, server, core = init_server_and_core()
    run_test(server, core)
