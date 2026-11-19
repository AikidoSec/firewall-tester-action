from testlib import *
from core_api import CoreApi


'''
1. Sets up a config with blocking on.
2. Sends a safe XML body to check that the demo app has the /api/create-xml route.
3. Sends the same SQL injection in element text and in attributes, at several depths.
4. Checks that each one is blocked, reported as a detection event and never inserted.
'''

PAYLOAD = "Malicious Pet', 'Gru from the Minions') --"
HEADERS = {"Content-Type": "application/xml"}

BODIES = {
    "element text": f"<pet><name>{PAYLOAD}</name></pet>",
    "nested element text": f"<order><pet><name>{PAYLOAD}</name></pet></order>",
    "attribute of a child element": f'<pets><pet name="{PAYLOAD}"/></pets>',
    "attribute of a nested element": f'<order><pets><pet name="{PAYLOAD}"/></pets></order>',
    "attribute of the root element": f'<pet name="{PAYLOAD}"/>',
}


def check_route_exists(collector, s):
    response = s.post_raw("/api/create-xml", "<pet><name>Bobby</name></pet>", HEADERS)
    return collector.soft_assert_response_code_is(
        response, 200, "Safe XML body to /api/create-xml (is the route implemented?)")


def check_xml_injection(collector, s, c, description, body):
    start_events = c.get_events("detected_attack")
    response = s.post_raw("/api/create-xml", body, HEADERS)
    collector.soft_assert_response_code_is(response, 500, f"SQL injection in XML {description}")

    c.wait_for_new_events(20, old_events_length=len(
        start_events), filter_type="detected_attack")
    new_events = c.get_events("detected_attack")[len(start_events):]
    if not collector.soft_assert(len(new_events) >= 1,
                                 f"No detection event for SQL injection in XML {description}"):
        return
    try:
        assert_event_contains_subset_file(new_events[0], "expect_detection_blocked.json")
    except AssertionError as e:
        collector.add_failure(f"SQL injection in XML {description}: {e}")


def check_nothing_inserted(collector, s):
    pets = s.get("/api/pets/")
    if collector.soft_assert_response_code_is(pets, 200, "Reading pets after the XML payloads"):
        collector.soft_assert("Gru" not in pets.text, "Bypass: an XML payload was inserted")


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    s.get("/clear")
    if not check_route_exists(collector, s):
        collector.raise_if_failures()
    for description, body in BODIES.items():
        check_xml_injection(collector, s, c, description, body)
    check_nothing_inserted(collector, s)

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
