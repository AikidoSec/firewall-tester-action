from testlib import *
from core_api import CoreApi


'''
1. Sets up a simple config and env AIKIDO_BLOCK=1
2. Send some attacks and check that they are blocked.
3. Update the config to disable blocking (forceProtectionOff: true) and check that the attacks are not blocked.
4. Update the config to enable blocking, and check that the attacks are blocked.
'''


def check_force_protection_off(collector, s, response_code, *, phase):
    # shell injection
    response = s.post("/api/execute", {"userCommand": "whoami"})
    collector.soft_assert_response_code_is(response, response_code, f"Shell injection {phase}")

    # sql injection
    response = s.post(
        "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"})
    collector.soft_assert_response_code_is(response, response_code, f"SQL injection {phase}")

    # path traversal
    response = s.get("/api/read?path=../secrets/key.txt")
    collector.soft_assert_response_code_is(response, response_code, f"Path traversal {phase}")


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    check_force_protection_off(collector, s, 500, phase="before applying forceProtectionOff")

    c.update_runtime_config_file("change_config_force_protection_off.json")
    check_force_protection_off(collector, s, 200, phase="while forceProtectionOff is active for this route")

    # chechk that rate limiting it's not impacted by force protection off
    for i in range(5):
        response = s.get("/test_ratelimiting_1")
        collector.soft_assert_response_code_is(
            response, 200, f"GET /test_ratelimiting_1 request {i + 1} is within this route's five-request limit"
        )

    for i in range(10):
        response = s.get("/test_ratelimiting_1")
        if i < 5:
            pass
        else:
            collector.soft_assert_response_code_is(
                response, 429,
                f"GET /test_ratelimiting_1 request {i + 6} exceeds its limit while protection is off on other routes",
            )

    c.update_runtime_config_file("start_config.json")
    check_force_protection_off(collector, s, 500, phase="after restoring protection on this route")

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
