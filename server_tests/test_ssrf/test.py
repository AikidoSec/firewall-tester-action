import requests
import time
import sys
from testlib import *
from core_api import CoreApi
import itertools
import os

'''
1. Sets up a simple config and env AIKIDO_BLOCK=1
2. Test that the firewall blocks SSRF attacks
3. Sends an attack request to check the blocking event is submitted
4. Change the config to disable blocking
5. Test that the firewall does not block SSRF attacks
6. Change the config to enable blocking
7. Test that the firewall blocks SSRF attacks
'''


def start_mock_servers(target_container_name: str):
    path = os.path.join(os.path.dirname(__file__), "mock-4000.sh")
    subprocess.run(
        f"docker run -d --name mock-4000-for-ssrf -v {path}:/mock-4000.sh:ro --network container:{target_container_name} alpine:3.20 sh /mock-4000.sh", shell=True)

    path = os.path.join(os.path.dirname(__file__), "mock-imds.py")
    subprocess.run(
        f"docker run -d --name mock-imds -v {path}:/mock-imds.py:ro --network container:{target_container_name} --cap-add NET_ADMIN python:3.12-alpine sh -c 'apk add --no-cache iproute2 && python /mock-imds.py 169.254.169.254 100.100.100.200'", shell=True)
    time.sleep(20)


def prefixnum(num, base):
    prefixes = {8: '0', 16: '0x'}
    if base == 8:
        return f"{prefixes[8]}{num:o}"
    elif base == 10:
        return str(num)
    elif base == 16:
        return f"{prefixes[16]}{num:x}"


def classify(addr, classN):
    if classN == 'C':
        return [addr[0], addr[1], addr[2], addr[3]]
    elif classN == 'B':
        val = (addr[2] << 8) | addr[3]
        return [addr[0], addr[1], val]
    elif classN == 'A':
        val = (addr[1] << 16) | (addr[2] << 8) | addr[3]
        return [addr[0], val]
    elif classN == '(whole network)':
        val = (addr[0] << 24) | (addr[1] << 16) | (addr[2] << 8) | addr[3]
        return [val]


def generate_combinations(ip_str):
    addr = [int(x) for x in ip_str.strip().split('.')]
    classes = ['C', 'B', 'A', '(whole network)']
    all_results = []
    bases = [8, 10, 16]

    for cls in classes:
        parts = classify(addr, cls)
        n = len(parts)
        # all combinations of bases for each part
        for base_combo in itertools.product(bases, repeat=n):
            rep = '.'.join(prefixnum(num, base)
                           for num, base in zip(parts, base_combo))
            all_results.append(rep)

    return all_results


def check_ssrf_with_event(response_code, expected_json):
    start_events = c.get_events()
    response = s.post(
        "/api/request", {"url": "http://127.0.0.1:9081"}, timeout=10)
    assert_response_code_is(response, response_code)

    c.wait_for_new_events(5, old_events_length=len(start_events))

    all_events = c.get_events()
    new_events = all_events[len(start_events):]

    assert_events_length_is(new_events, 1)
    # assert_started_event_is_valid(all_events[0])
    assert_event_contains_subset_file(new_events[0], expected_json)


def check_ssrf(route, ip):
    response = s.post(route, {"url": ip}, timeout=10)
    assert_response_code_is(
        response, 500, f"[{route}] SSRF check failed for {ip} {response.text}")


def run_test(s: TestServer, c: CoreApi):

    check_ssrf_with_event(500, "expect_detection_blocked.json")

    c.update_runtime_config_file("change_config_disable_blocking.json")
    check_ssrf_with_event(400, "expect_detection_not_blocked.json")

    c.update_runtime_config_file("start_config.json")
    check_ssrf_with_event(500, "expect_detection_blocked.json")

    ips = [
        #     This is not a domain, but it will return 500
        "http://this.is.not.a.domain.com:8081",
        "http://localhost:4000",
        "http://LOCALHOST:4000",
        "http://loopback:4000",
        "http://0:4000",
        "http://0.0.0.0:4000",
        "http://[::1]:4000",
        "http://[0000:0000:0000:0000:0000:0000:0000:0001]:4000",
        "http://[::]:4000",
        "http://[0:0:0:0:0:0:0:1]:4000",
        "http://[::ffff:127.0.0.1]:4000",
        "http://[0:0::1]:4000",
        "http://127%2E0%2E0%2E1:4000",
        "http://%30:4000",


        # AWS metadata service
        "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
        "http://0251.0376.0251.0376/latest/meta-data/iam/security-credentials/",
        "http://[fd00:0ec2:0000:0000:0000:0000:0000:0254]:7000/latest/meta-data/iam/security-credentials/",
        "http://0xa9.0xfe.0xa9.0xfe/latest/meta-data/iam/security-credentials/",
        "http://0251.0376.0124776/latest/meta-data/iam/security-credentials/",
        "http://0xA9FEA9FE/latest/meta-data/iam/security-credentials/",
        "http://2852039166/latest/meta-data/iam/security-credentials/",
        "http://[::ffff:169.254.169.254]:8081/latest/meta-data/iam/security-credentials/",
        "http://[fd00:ec2::254]/latest/meta-data/iam/security-credentials/"
    ]
    ips.extend(
        [f"http://{ip}:80" for ip in generate_combinations("169.254.169.254")])
    # 100.100.100.200
    ips.extend(
        [f"http://{ip}:80" for ip in generate_combinations("100.100.100.200")])
    ips.extend(
        [f"http://{ip}:4000" for ip in generate_combinations("127.0.0.1")])

    # SSRF redirect tests
    ips.extend([
        "http://ssrf-redirects.testssandbox.com/ssrf-test",
        "http://ssrf-rédirects.testssandbox.com/ssrf-test",
        "http://xn--ssrf-rdirects-ghb.testssandbox.com/ssrf-test",
        "http://ssrf-r%C3%A9directs.testssandbox.com/ssrf-test",
    ])
    for ip in ips:
        check_ssrf("/api/request", ip)
        check_ssrf("/api/request2", ip)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    try:
        start_mock_servers("test_ssrf")
        run_test(s, c)
    finally:
        subprocess.run(
            f"docker rm -f mock-4000-for-ssrf", shell=True)
        subprocess.run(
            f"docker rm -f mock-imds", shell=True)
