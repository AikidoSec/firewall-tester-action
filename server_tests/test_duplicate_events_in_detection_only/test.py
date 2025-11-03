from testlib import *
from core_api import CoreApi




def check_path_traversal():
    start_events = c.get_events("detected_attack")
    response = s.get("/api/read?path=../secrets/key.txt")
    assert_response_code_is(response, 200,
                            f"Path traversal check failed {response.text}")

    c.wait_for_new_events(20, old_events_length=len(
        start_events), filter_type="detected_attack")

    all_events = c.get_events("detected_attack")
    new_events = all_events[len(start_events):]

    assert_events_length_is(new_events, 1)
   

def check_shell_injection():
    start_events = c.get_events("detected_attack")
    response = s.post("/api/execute", {"userCommand": "whoami"})
    assert_response_code_is(response, 200)

    c.wait_for_new_events(5, old_events_length=len(
        start_events), filter_type="detected_attack")

    all_events = c.get_events("detected_attack")
    new_events = all_events[len(start_events):]

    assert_events_length_is(new_events, 1)


def check_ssrf():
    start_events = c.get_events("detected_attack")
    response = s.post(
        "/api/request", {"url": "http://127.0.0.1:4000"}, timeout=10)
    assert_response_code_is(response, 200)

    c.wait_for_new_events(5, old_events_length=len(
        start_events), filter_type="detected_attack")

    all_events = c.get_events("detected_attack")
    new_events = all_events[len(start_events):]

    assert_events_length_is(new_events, 1)


def run_test(s: TestServer, c: CoreApi):
    check_path_traversal()
    check_shell_injection()
    check_ssrf()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
