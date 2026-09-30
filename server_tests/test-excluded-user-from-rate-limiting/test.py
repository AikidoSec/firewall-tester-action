
import time
from testlib import *
from core_api import CoreApi


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    ip = "2.16.53.5"

    # Step 1: Non-excluded user is rate-limited on /api/pets (limit: 5 req/min)
    for _ in range(5):
        response = s.get(
            "/api/pets/", headers={"X-Forwarded-For": ip, "X-User-ID": "99990001", "X-User-Name": "TestUser"})
        collector.soft_assert_response_code_is(
            response, 200, "Non-excluded user should not be rate-limited within limit")

    for i in range(10):
        response = s.get(
            "/api/pets/", headers={"X-Forwarded-For": ip, "X-User-ID": "99990001", "X-User-Name": "TestUser"})
        if i >= 5:
            collector.soft_assert_response_code_is(
                response, 429, "Non-excluded user should be rate-limited after exceeding limit")

    # Step 2: Excluded user 21110001 is not rate-limited on /api/pets/
    for _ in range(20):
        response = s.get("/api/pets/", headers={"X-Forwarded-For": ip,
                         "X-User-ID": "21110001", "X-User-Name": "ExcludedUser1"})
        collector.soft_assert_response_code_is(
            response, 200, "Excluded user 21110001 should never be rate-limited on /api/pets/")

    # Step 3: Excluded user 21110002 is not rate-limited on /api/pets/
    for _ in range(20):
        response = s.get("/api/pets/", headers={"X-Forwarded-For": ip,
                         "X-User-ID": "21110002", "X-User-Name": "ExcludedUser2"})
        collector.soft_assert_response_code_is(
            response, 200, "Excluded user 21110002 should never be rate-limited on /api/pets/")

    # Step 4: Excluded user 21110001 is not rate-limited on /test_ratelimiting_1 (limit: 10 req/min)
    for _ in range(20):
        response = s.get("/test_ratelimiting_1", headers={
                         "X-Forwarded-For": ip, "X-User-ID": "21110001", "X-User-Name": "ExcludedUser1"})
        collector.soft_assert_response_code_is(
            response, 200, "Excluded user 21110001 should never be rate-limited on /test_ratelimiting_1")

    # Step 5: Excluded user bypasses rate limiting even when they belong to a rate limiting group
    # First, exhaust the rate limit for a group using requests with no user set
    group_cookie = "RateLimitingGroupID=EXCL_TEST_GROUP"
    for _ in range(5):
        response = s.get(
            "/api/pets/", headers={"X-Forwarded-For": ip, "Cookie": group_cookie})
        collector.soft_assert_response_code_is(
            response, 200, "Group requests within limit should be 200")

    for i in range(10):
        response = s.get(
            "/api/pets/", headers={"X-Forwarded-For": ip, "Cookie": group_cookie})
        if i >= 5:
            collector.soft_assert_response_code_is(
                response, 429, "Group should be rate-limited after exceeding limit")

    # Now send requests as excluded user 21110001 with the same group cookie that is rate-limited
    # The excluded user should bypass rate limiting even though their group is exhausted
    for _ in range(20):
        response = s.get("/api/pets/", headers={"X-Forwarded-For": ip, "Cookie": group_cookie,
                         "X-User-ID": "21110001", "X-User-Name": "ExcludedUser1"})
        collector.soft_assert_response_code_is(
            response, 200, "Excluded user 21110001 should bypass rate limiting even when belonging to a rate-limited group")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
