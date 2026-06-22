from testlib import *
from core_api import CoreApi


'''
1. Sets up a simple config and env AIKIDO_BLOCK=1.
2. Starts a mock server on port 4000.
3. Send a request to the server with a body that contains a url and a port. 
4. The server will change the port in the URL and send a request to the new URL.
5. The server should not block the request.
'''


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()
    response = s.post("/api/request_different_port",
                      {"url": "http://127.0.0.1:4001", "port": "4000"})
    collector.soft_assert_response_code_is(
        response, 200, f"Aikido Zen should not block the request {response.text}")
    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
