from testlib import *
from core_api import CoreApi


'''
Tests that rate-limited responses include a valid Retry-After header.

1. Configure rate limiting: 3 requests per 60 s on /test_ratelimiting_1.
2. Send 3 requests — all should return 200 (no Retry-After header).
3. Send more requests — should return 429 with a Retry-After header
   whose value is a positive integer (seconds until the window resets).
4. Verify Retry-After is present and its value is a reasonable number
   of seconds (between 1 and 60 for a 60 s window).
'''


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    client_ip = "4.18.92.7"
    headers = {"X-Forwarded-For": client_ip}

    # Phase 1: send requests up to the limit — should all succeed
    for i in range(3):
        response = s.get("/test_ratelimiting_1", headers=headers)
        collector.soft_assert_response_code_is(
            response, 200, f"Request {i+1}/3 should succeed")
        if response and "Retry-After" in response.headers:
            collector.soft_assert(
                False,
                f"Request {i+1}/3 should NOT have Retry-After header "
                f"(got {response.headers['Retry-After']})")

    # Phase 2: next requests should be rate limited with Retry-After
    for i in range(5):
        response = s.get("/test_ratelimiting_1", headers=headers)
        if not collector.soft_assert_response_code_is(
                response, 429,
                f"Request {i+1}/5 after limit should be 429"):
            continue

        has_header = collector.soft_assert(
            response is not None and "Retry-After" in response.headers,
            f"Rate-limited response {i+1}/5 missing Retry-After header "
            f"(headers: {dict(response.headers) if response else 'None'})")

        if has_header:
            retry_after = response.headers["Retry-After"]
            is_numeric = retry_after.isdigit()
            collector.soft_assert(
                is_numeric,
                f"Retry-After should be a numeric value, got '{retry_after}'")
            if is_numeric:
                seconds = int(retry_after)
                collector.soft_assert(
                    1 <= seconds <= 60,
                    f"Retry-After should be between 1 and 60 seconds "
                    f"(60s window), got {seconds}")

    # Phase 3: different IP should NOT be rate limited
    other_ip = "9.22.33.44"
    other_headers = {"X-Forwarded-For": other_ip}
    for i in range(3):
        response = s.get("/test_ratelimiting_1", headers=other_headers)
        collector.soft_assert_response_code_is(
            response, 200,
            f"Request from different IP should not be rate limited")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
