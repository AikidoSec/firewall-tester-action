import ipaddress
import uuid

from core_api import CoreApi
from testlib import TestServer, assert_response_code_is, init_server_and_core


AGENT_HEADERS = (
    "X-Agent-Platform",
    "X-Agent-Version",
    "X-Agent-Hostname",
    "X-Agent-IP-Address",
    "X-Agent-Session-Id",
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
    expected_headers = events[0]["requestHeaders"]

    for event in events:
        headers = event["requestHeaders"]
        assert headers == expected_headers, (
            f"Agent request headers changed from {expected_headers} to {headers}"
        )
        for header in AGENT_HEADERS:
            assert isinstance(headers.get(header), str) and headers[header], (
                f"Expected {header} on the {event['type']} event, got {headers}"
            )

        agent = event["agent"]
        assert headers["X-Agent-Version"] == agent["version"]
        assert headers["X-Agent-Hostname"] == agent["hostname"]
        assert headers["X-Agent-IP-Address"] == agent["ipAddress"]

    assert expected_headers["X-Agent-Platform"].lower() != "unknown"
    assert expected_headers["X-Agent-Version"].lower() != "unknown"

    session_id = uuid.UUID(expected_headers["X-Agent-Session-Id"])
    assert session_id.version in (4, 7)
    assert session_id.variant == uuid.RFC_4122

    agent_ip_address = expected_headers["X-Agent-IP-Address"]
    if agent_ip_address != "unknown":
        ipaddress.ip_address(agent_ip_address)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
