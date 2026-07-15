import time
from testlib import *
from core_api import CoreApi

'''
1. Sets up the rate limiting config to 5 requests / minute for route '/test_ratelimiting_*'.
2. Sends 5 requests to '/test_ratelimiting_<1 or 2>'. Checks that those requests are not blocked.
3. Send another more 5 request to '/test_ratelimiting_*'. Checks that they all are rate limited.
4. Sends 100 requests to another route '/api/pets'. Checks that those requests are not blocked.
5. Sends 1 request to '/api/pets'. Checks that it is rate limited.
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
        if i < 5:
            pass
        else:
            collector.soft_assert_response_code_is(response, 429, response.text)

    for _ in range(100):
        response = s.get(
            "/api/pets/", headers={"X-Forwarded-For": "2.16.53.5"})
        collector.soft_assert_response_code_is_not(response, 429, response.text)

    response = s.get("/api/pets/", headers={"X-Forwarded-For": "2.16.53.5"})
    collector.soft_assert_response_code_is(response, 429, response.text)

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
