from testlib import *
from core_api import CoreApi


'''
1. Sets up a simple config and env AIKIDO_BLOCK=1
2. Send some attacks and check that they are blocked.
3. Update the config to disable blocking (forceProtectionOff: true) and check that the attacks are not blocked.
4. Update the config to enable blocking, and check that the attacks are blocked.
'''


def start_mock_servers(target_container_name: str):
    path = os.path.join(os.path.dirname(__file__), "mock-4000.sh")
    subprocess.run(
        f"docker run -d --name mock-4000-for-ssrf-{target_container_name} -v {path}:/mock-4000.sh:ro --network container:{target_container_name} alpine:3.20 sh /mock-4000.sh", shell=True)

    time.sleep(20)


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

    # ssrf
    response = s.post(
        "/api/request", {"url": "http://127.0.0.1:4000"}, timeout=10)
    assert_response_code_is(response, response_code, "ssrf")


def run_test(s: TestServer, c: CoreApi):
    check_force_protection_off(500)

    c.update_runtime_config_file("change_config_force_protection_off.json")
    check_force_protection_off(200)

    c.update_runtime_config_file("start_config.json")
    check_force_protection_off(500)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    try:
        start_mock_servers("test_force_protection_off")
        run_test(s, c)
    finally:
        subprocess.run(
            f"docker rm -f mock-4000-for-ssrf-test_force_protection_off", shell=True)
