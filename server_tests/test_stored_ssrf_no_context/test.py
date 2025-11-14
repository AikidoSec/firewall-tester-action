
import time
from testlib import *
from core_api import CoreApi
import os

'''
Stored SSRF Attack Detection Test (No Request Context)

This test verifies that the firewall can detect and report stored SSRF attacks that occur 
outside of the original HTTP request context (e.g., in background threads, async tasks, or delayed jobs).

Test Steps:
1. Start mock IMDS server that adds IMDS IP address (169.254.169.254) to the lo interface
2. Add entry to /etc/hosts to resolve evil-stored-ssrf-hostname to 169.254.169.254
3. Send POST request to /api/stored_ssrf_2 - returns 200 immediately (starts background thread)
4. Background thread waits 10 seconds, then makes SSRF request to evil-stored-ssrf-hostname
5. Wait up to 30 seconds for the firewall to detect the attack and submit event to core
6. Verify that a "detected_attack" event is submitted with attack details
'''


def set_etc_hosts(target_container_name: str, ip: str, hostname: str):
    subprocess.run(
        f"docker exec  -u 0 {target_container_name} sh -c 'echo {ip} {hostname} >> /etc/hosts'", shell=True)
    time.sleep(5)


def start_mock_servers(target_container_name: str):
    path = os.path.join(os.path.dirname(__file__), "mock-imds.py")
    subprocess.run(
        f"docker run -d --name {target_container_name}-mock-imds -v {path}:/mock-imds.py:ro --network container:{target_container_name} --cap-add NET_ADMIN python:3.12-alpine sh -c 'apk add --no-cache iproute2 && python /mock-imds.py 169.254.169.254'", shell=True)
    i = 0
    while True:
        time.sleep(1)
        if subprocess.run(
                f"docker ps | grep {target_container_name}-mock-imds | grep Up", shell=True).returncode == 0:
            break
        time.sleep(1)
        i += 1
        if i > 20:
            raise Exception(
                f"Mock IMDS server did not start after {i} seconds")


def check_ssrf_with_event(response_code, expected_json):
    start_events = c.get_events("detected_attack")
    response = s.post("/api/stored_ssrf_2", timeout=10)
    assert_response_code_is(response, response_code, f"[{response.text}]")

    c.wait_for_new_events(30, old_events_length=len(
        start_events), filter_type="detected_attack")

    all_events = c.get_events("detected_attack")
    new_events = all_events[len(start_events):]

    assert_events_length_at_least(new_events, 1)
    assert_event_contains_subset_file(new_events[0], expected_json)


def run_test(s: TestServer, c: CoreApi, target_container_name: str):
    set_etc_hosts(target_container_name, "169.254.169.254",
                  "evil-stored-ssrf-hostname")
    check_ssrf_with_event(200, "expect_detection_blocked.json")


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    target_container_name = "test_stored_ssrf_no_context"
    try:
        start_mock_servers(target_container_name)
        run_test(s, c, target_container_name)
    finally:
        subprocess.run(
            f"docker rm -f {target_container_name}-mock-imds", shell=True)
