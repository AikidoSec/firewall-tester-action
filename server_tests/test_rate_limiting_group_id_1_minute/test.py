import requests
import time
import sys
from testlib import *
from core_api import CoreApi
import os


'''
Test for rate limiting group id 
'''


def get_random_ip():
    return f"2.16.53.{random.randint(1, 255)}"


def run_test(s: TestServer, c: CoreApi):
    # RateLimitingGroupID=1234567890
    cookie = "RateLimitingGroupID=1234567890"
    for _ in range(5):
        response = s.get(
            "/",  headers={"X-Forwarded-For": get_random_ip(), "Cookie": cookie})
        assert_response_code_is(response, 200)

    # sleep for 10 seconds
    time.sleep(10)

    for i in range(10):
        response = s.get(
            "/", headers={"X-Forwarded-For": get_random_ip(), "Cookie": cookie})
        if i < 5:
            pass
        else:
            assert_response_code_is(response, 429)

    for _ in range(100):

        response = s.get(
            "/api/pets/", headers={"X-Forwarded-For": get_random_ip(), "Cookie": cookie})
        assert_response_code_is(response, 200)

    for i in range(10):
        response = s.get(
            "/api/pets/", headers={"X-Forwarded-For": get_random_ip(), "Cookie": cookie})
        assert_response_code_is(response, 429, "Expected 429 for /api/pets/")

    tests = [
        "/api/pets", "/api/pets/", "/api//pets", "//api/pets",
        "/api/./pets", "/api/pets/.", "/api/pets/../pets",
        "/API/pets", "/api/PETS",
        "/api/%70ets", "/%61pi/pets", "/api/p%65ts", "/api/pet%73",
        "/api/%2570ets", "/api/p%2565ts", "/api/pet%2573",
        "/%61pi/%70%65ts", "/%2fapi%2fpets", "/api/%2E/pets", "/api/pets%2F",
        "/api/././pets", "/api/alpha/../pets", "/api/alpha/../../api/pets",
        "/api///pets", "///api///pets///",
        "\\api\\pets", "/api\\pets", "\\api/pets",
        "/api/pets?id=1", "/api/pets?", "/api/pets?#fragment",
        "/api/pets;v=1", "/api;v=1/pets", "/api/pets;foo=bar",
        "/api/péts", "/api/péts", "/api/pets%C3%A9",
        "/api/pets%00", "/api/pets(%20)", "/api/pets..",
        "/api/pets.;", "/api/pets.%2E", "/api/pets.json",
        "/api/pets%2f..%2fsecret", "/api/pets%2f/", "/api/%2e%2e/pets"
    ]

    for test in tests:
        response = s.get_raw(
            test, headers={"X-Forwarded-For": get_random_ip(), "Cookie": cookie})

        assert_response_code_is_not(
            response, 200, f"Should not be 200 for {test} ")

    for i in range(10):
        response = s.get_raw(
            "/test_ratelimiting_1", headers={"X-Forwarded-For": get_random_ip(), "Cookie": cookie})
        assert_response_code_is(
            response, 200, "Expected 200 for /test_ratelimiting_1")

    tests = [
        "/test_ratelimiting_1", "/test_ratelimiting_1/", "/test__ratelimiting_1", "//test_ratelimiting_1",
        "/test_ratelimiting_1/.", "/test_ratelimiting_1/../test_ratelimiting_1", "/TEST_RATELIMITING_1", "/test_RATELIMITING_1",
        "/%74est_ratelimiting_1", "/t%65st_ratelimiting_1", "/tes%74_ratelimiting_1", "/test_%72atelimiting_1",
        "/test_ratelimitin%67_1", "/test_ratelimiting_%31", "/%2574est_ratelimiting_1", "/test_ratelimiting_%2531",
        "/%2ftest_ratelimiting_1", "/test%2F_ratelimiting_1", "/test_ratelimiting_1%2F", "/test%2E_ratelimiting_1",
        "/./test_ratelimiting_1", "/test_ratelimiting_1/./", "/alpha/../test_ratelimiting_1", "/alpha/../../test_ratelimiting_1",
        "/test///ratelimiting_1", "///test_ratelimiting_1///",
        "\\test_ratelimiting_1", "/test_ratelimiting_1\\", "\\test_ratelimiting_1\\",
        "/test_ratelimiting_1?x=1", "/test_ratelimiting_1?", "/test_ratelimiting_1?#frag",
        "/test_ratelimiting_1;v=1", "/;v=1/test_ratelimiting_1",
        "/test_ratelimitiṅg_1", "/tést_ratelimiting_1", "/tést_ratelimiting_1", "/test_ratelimiting_1%C2%A0",
        "/test_ratelimiting_1%00", "/test_ratelimiting_1(%20)", "/test_ratelimiting_1..",
        "/test_ratelimiting_1.;", "/test_ratelimiting_1.%2E", "/test_ratelimiting_1.json",
        "/test_ratelimiting_1%2f..%2fsecret", "/test_ratelimiting_1%2f/", "/%2e%2e/test_ratelimiting_1"
    ]

    for test in tests:
        response = s.get_raw(
            test, headers={"X-Forwarded-For": get_random_ip(), "Cookie": cookie})
        assert_response_code_is_not(
            response, 200, f"Should not be 200 for {test} ")


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
