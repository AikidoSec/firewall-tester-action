import time
from testlib import *
from core_api import CoreApi

'''
User Rate Limiting Test (1 Minute Window with Enable/Disable)

This test verifies that the firewall correctly enforces user-based rate limiting per endpoint pattern,
and that rate limiting can be dynamically enabled and disabled via runtime configuration updates.

Test Steps:
1. Send 5 requests to /test_ratelimiting_<1 or 2> - verify none are rate limited (uses up the rate limit)
2. Wait 5 seconds
3. Send 10 requests to /test_ratelimiting_<1 or 2> - verify all 10 return 429 (rate limit exceeded)
4. Send 100 requests to /api/pets/ - verify none are rate limited
5. Send 1 more request to /api/pets/ - verify it is rate limited (429)
6. Update runtime config to disable rate limiting
7. Send 20 requests to /test_ratelimiting_<1 or 2> - verify none are rate limited
8. Update runtime config to re-enable rate limiting (resets counters)
9. Send 10 requests to /test_ratelimiting_<1 or 2> - verify none are rate limited (counter was reset)
10. Wait 5 seconds
11. Send 10 requests to /test_ratelimiting_<1 or 2> - verify all 10 return 429 (rate limit exceeded)

Note: Requests to /test_ratelimiting_1 and /test_ratelimiting_2 share the same rate limit counter
because they match the same pattern '/test_ratelimiting_*'.
'''


def get_random():
    return random.choice([1, 2])


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    for i in range(5):
        response = s.get(
            f"/test_ratelimiting_{get_random()}",  headers={"X-Forwarded-For": "2.16.53.5"})
        collector.soft_assert_response_code_is_not(response, 429, response.text)

    # sleep for 10 seconds
    time.sleep(5)

    for i in range(10):
        response = s.get(
            f"/test_ratelimiting_{get_random()}", headers={"X-Forwarded-For": "2.16.53.5"})
        collector.soft_assert_response_code_is(response, 429, response.text)

    for _ in range(100):
        response = s.get(
            "/api/pets/", headers={"X-Forwarded-For": "2.16.53.5"})
        collector.soft_assert_response_code_is_not(response, 429, response.text)

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "2.16.53.5"})
    collector.soft_assert_response_code_is(response, 429, response.text)

    c.update_runtime_config_file("disable_rate_limit.json")

    for i in range(20):
        response = s.get(
            f"/test_ratelimiting_{get_random()}",  headers={"X-Forwarded-For": "2.16.53.5"})
        collector.soft_assert_response_code_is_not(response, 429, response.text)

    # enable rate limiting and update max requests to 10 (reset counter)
    c.update_runtime_config_file("enable_rate_limit.json")

    for i in range(10):
        response = s.get(
            f"/test_ratelimiting_{get_random()}",  headers={"X-Forwarded-For": "2.16.53.5"})
        collector.soft_assert_response_code_is_not(response, 429, response.text)

    time.sleep(5)
    for i in range(10):
        response = s.get(
            f"/test_ratelimiting_{get_random()}",  headers={"X-Forwarded-For": "2.16.53.5"})
        collector.soft_assert_response_code_is(response, 429, response.text)

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
