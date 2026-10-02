import ipaddress
import uuid

from core_api import CoreApi
from testlib import TestServer, assert_response_code_is, init_server_and_core


AGENT_HEADERS = (
    "x-agent-platform",
    "x-agent-library",
    "x-agent-version",
    "x-agent-hostname",
    "x-agent-ip-address",
    "x-agent-session-id",
)


def get_start_event(c):
    events = c.get_events("started", include_headers=True)
    if not events:
        assert c.wait_for_new_events(10, 0, "started"), "Expected a startup event"
        events = c.get_events("started", include_headers=True)
    return events[-1]


def send_attack_and_get_event(s, c):
    existing_events = c.get_events("detected_attack")
    response = s.post("/api/execute", {"userCommand": "whoami"})
    assert_response_code_is(response, 500)
    assert c.wait_for_new_events(10, len(existing_events), "detected_attack"), (
        "Expected a detected attack event"
    )
    events = c.get_events("detected_attack", include_headers=True)
    return events[len(existing_events)]


def run_test(s: TestServer, c: CoreApi):
    events = [get_start_event(c), send_attack_and_get_event(s, c)]
    expected_headers = {
        header: events[0]["requestHeaders"].get(header)
        for header in AGENT_HEADERS
    }

    for event in events:
        headers = {
            header: event["requestHeaders"].get(header)
            for header in AGENT_HEADERS
        }
        assert headers == expected_headers, (
            f"Agent request headers changed from {expected_headers} to {headers}"
        )
        for header in AGENT_HEADERS:
            assert isinstance(headers[header], str) and headers[header], (
                f"Expected {header} on the {event['type']} event, got {headers}"
            )

        agent = event["agent"]
        assert headers["x-agent-library"] == agent["library"]
        assert headers["x-agent-version"] == agent["version"]
        assert headers["x-agent-hostname"] == agent["hostname"]
        assert headers["x-agent-ip-address"] == agent["ipAddress"]

    assert expected_headers["x-agent-platform"].lower() != "unknown"
    assert expected_headers["x-agent-version"].lower() != "unknown"

    session_id = uuid.UUID(expected_headers["x-agent-session-id"])
    assert session_id.version in (4, 7)
    assert session_id.variant == uuid.RFC_4122

    agent_ip_address = expected_headers["x-agent-ip-address"]
    if agent_ip_address != "unknown":
        ipaddress.ip_address(agent_ip_address)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
