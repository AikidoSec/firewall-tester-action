import requests
import time
import sys
from testlib import *
from core_api import CoreApi
import os


'''
1. Sets up a simple config and env AIKIDO_BLOCK=1.
2. Starts a mock server on port 4000.
3. Send a request to the server with a body that contains a url and a port. 
4. The server will change the port in the URL and send a request to the new URL.
5. The server should not block the request.
'''


def start_mock_servers(target_container_name: str):
    path = os.path.join(os.path.dirname(__file__), "mock-4000.sh")
    subprocess.run(
        f"docker run -d --name mock-4000-for-php -v {path}:/mock-4000.sh:ro --network container:{target_container_name} alpine:3.20 sh /mock-4000.sh", shell=True)
    time.sleep(20)


def run_test(s: TestServer, c: CoreApi):
    try:
        container_name = "test_ssrf_diffrent_port"
        start_mock_servers(container_name)
        response = s.post("/api/request_different_port",
                          {"url": "http://127.0.0.1:4001", "port": "4000"})
        assert_response_code_is_not(
            response, 500, f"Aikido Zen should not block the request {response.text}")
    finally:
        subprocess.run(
            f"docker rm -f mock-4000-for-php", shell=True)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
