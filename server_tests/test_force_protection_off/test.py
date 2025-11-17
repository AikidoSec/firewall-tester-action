from testlib import *
from core_api import CoreApi


'''
1. Sets up a simple config and env AIKIDO_BLOCK=1
2. Send some attacks and check that they are blocked.
3. Update the config to disable blocking (forceProtectionOff: true) and check that the attacks are not blocked.
4. Update the config to enable blocking, and check that the attacks are blocked.
'''


def check_force_protection_off(response_code):
    # shell injection
    response = s.post("/api/execute", {"userCommand": "whoami"})
    assert_response_code_is(response, response_code, "shell injection")

    # sql injection
    response = s.post(
        "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"})
    assert_response_code_is(response, response_code, "sql injection")

    # path traversal
    response = s.get("/api/read?path=../secrets/key.txt")
    assert_response_code_is(response, response_code, "path traversal")


def run_test(s: TestServer, c: CoreApi):
    check_force_protection_off(500)

    c.update_runtime_config_file("change_config_force_protection_off.json")
    check_force_protection_off(200)

    # chechk that rate limiting it's not impacted by force protection off
    for i in range(5):
        response = s.get("/test_ratelimiting_1")
        assert_response_code_is(response, 200, response.text)

    for i in range(10):
        response = s.get("/test_ratelimiting_1")
        if i < 5:
            pass
        else:
            assert_response_code_is(response, 429, response.text)

    c.update_runtime_config_file("start_config.json")
    check_force_protection_off(500)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
