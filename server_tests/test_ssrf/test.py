import requests
import time
import sys
from testlib import *
from core_api import CoreApi
import os
import logging

'''
1. Sets up a simple config and env AIKIDO_BLOCK=1.
2. Sends an attack request to a route, that will cause sending a detection event.
3. Checks that the detection event was submitted and is valid.
'''


def check_ssrf(ip, expected_json):
    response = s.post("/api/request", {"url": ip}, timeout=10)
    assert_response_code_is(response, 500, f"SSRF check failed for {ip}")


def run_test(s: TestServer, c: CoreApi):
    ips = [
        "http://127.0.0.1:9081",
        "http://this.is.not.a.domain.com:8081",
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
        "http://[::]:8081",
        "http://[0:0:0:0:0:0:0:1]:8081",
        "http://[::ffff:127.0.0.1]:8081",
        "http://ssrf-rédirects.testssandbox.com/ssrf-test",
        "http://xn--ssrf-rdirects-ghb.testssandbox.com/ssrf-test",
        "http://ssrf-redirects.testssandbox.com/ssrf-test",

    ]
    for ip in ips:
        check_ssrf(ip, "expect_detection_blocked.json")
    pass


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
