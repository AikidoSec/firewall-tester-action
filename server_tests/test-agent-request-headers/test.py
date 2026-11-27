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
    assert c.wait_for_new_events(10, 0, "started"), "Expected a startup event"
    return c.get_events("started", include_headers=True)[-1]


def send_attack_and_get_event(s, c):
    existing_events = c.get_events("detected_attack")
    response = s.post("/api/execute", {"userCommand": "whoami"})
    assert_response_code_is(
        response, 500,
        "The agent should block the request that generates the detection event used for header checks",
    )
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
        for header in AGENT_HEADERS:
            value = headers.get(header)
            assert isinstance(value, str) and value, (
                f"Expected {header} on the {event['type']} event, got {headers}"
            )
            assert value == expected_headers.get(header), (
                f"{header} changed from {expected_headers.get(header)} to {value}"
            )

        agent = event["agent"]
        for header, field in (
            ("x-agent-library", "library"),
            ("x-agent-version", "version"),
            ("x-agent-hostname", "hostname"),
            ("x-agent-ip-address", "ipAddress"),
        ):
            assert headers[header] == agent[field], (
                f"{event['type']} event sent {header}={headers[header]!r}, "
                f"expected {agent[field]!r} from agent.{field}"
            )

    for header in ("x-agent-platform", "x-agent-version"):
        assert expected_headers[header].lower() != "unknown", (
            f"The startup event must report a known value for {header}"
        )

    session_id = uuid.UUID(expected_headers["x-agent-session-id"])
    assert session_id.version in (4, 7), (
        f"Expected x-agent-session-id to use UUID version 4 or 7, got {session_id.version}"
    )
    assert session_id.variant == uuid.RFC_4122, (
        f"Expected x-agent-session-id to use the RFC 4122 variant, got {session_id.variant}"
    )

    agent_ip_address = expected_headers["x-agent-ip-address"]
    if agent_ip_address != "unknown":
        ipaddress.ip_address(agent_ip_address)


if __name__ == "__main__":
    _, s, c = init_server_and_core()
    run_test(s, c)
