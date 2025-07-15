import requests
import time
import sys
from testlib import *
from core_api import CoreApi
import os

'''
1. Sets up a simple config and env AIKIDO_BLOCK=1
2. Test that the firewall blocks SSRF attacks
3. Sends an attack request to check the blocking event is submitted
4. Change the config to disable blocking
5. Test that the firewall does not block SSRF attacks
6. Change the config to enable blocking
7. Test that the firewall blocks SSRF attacks
'''


def check_ssrf_with_event(response_code, expected_json):
    start_events = c.get_events()
    response = s.post("/api/request", {"url": "http://127.0.0.1:9081"}, timeout=10)
    assert_response_code_is(response, response_code)
   

    c.wait_for_new_events(5, old_events_length=len(start_events))

    all_events = c.get_events()
    new_events = all_events[len(start_events):]

    assert_events_length_is(new_events, 1)
    assert_started_event_is_valid(all_events[0])
    assert_event_contains_subset_file(new_events[0], expected_json)


def check_ssrf(ip):
    response = s.post("/api/request", {"url": ip}, timeout=10)
    assert_response_code_is(response, 500, f"SSRF check failed for {ip} {response.text}")

def run_test(s: TestServer, c: CoreApi):
    
    check_ssrf_with_event(500, "expect_detection_blocked.json")

    c.update_runtime_config_file("change_config_disable_blocking.json")
    check_ssrf_with_event(400, "expect_detection_not_blocked.json")

    c.update_runtime_config_file("start_config.json")
    check_ssrf_with_event(500, "expect_detection_blocked.json")

    ips = [
        "http://127.0.0.1:9081",
        "http://this.is.not.a.domain.com:8081", # This is not a domain, but it will return 500 
        "http://localhost:8081",
        "http://2130706433:8081",
        "http://0x7f000001:8081",
        "http://0177.0.0.01:8081",
        "http://0x7f.0x0.0x0.0x1:8081",
        "http://LOCALHOST:8081",
        "http://loopback:8081",
        "http://127.1:8081",
        "http://0x7f.1:8081",
        "http://0:8081",
        "http://0.0.0.0:8081",
        "http://[::1]:8081",
        "http://[0000:0000:0000:0000:0000:0000:0000:0001]:8081",
        "http://[::]:8081",
        "http://[0:0:0:0:0:0:0:1]:8081",
        "http://[::ffff:127.0.0.1]:8081",
        "http://ssrf-redirects.testssandbox.com/ssrf-test",
        "http://ssrf-rédirects.testssandbox.com/ssrf-test",
        "http://xn--ssrf-rdirects-ghb.testssandbox.com/ssrf-test", 
    ]
    for ip in ips:
        check_ssrf(ip)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
