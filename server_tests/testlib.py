import datetime
import time
import requests
import argparse
from requests.adapters import HTTPAdapter, Retry
s = requests.Session()
retries = Retry(connect=10,
                backoff_factor=1)

s.mount('http://', HTTPAdapter(max_retries=retries))

def localhost_get_request(port, route="", headers={}, benchmark=False):
    global benchmarks, s

    start_time = datetime.datetime.now()

    r = s.get(f"http://localhost:{port}{route}", headers=headers)

    end_time = datetime.datetime.now()    
    delta = end_time - start_time
    elapsed_ms = delta.total_seconds() * 1000
    
    if benchmark:
        benchmarks.append(elapsed_ms)
        
    time.sleep(0.001)
    return r

def load_test_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server_port", type=int, required=True)
    parser.add_argument("--token", type=str, required=True)
    parser.add_argument("--core_port", type=int, default=3000)
    parser.add_argument("--config_update_delay", type=int, default=60)
    args = parser.parse_args()
    return args

class TestServer:
    def __init__(self, port: int, token: str):
        self.port = port
        self.token = token

    def get(self, route="", headers={}, benchmark=False):
        return localhost_get_request(self.port, route, headers, benchmark)





def assert_response_code_is(response, status_code):
    assert response.status_code == status_code, f"Status codes are not the same: {response.status_code} vs {status_code}"
    
def assert_response_header_contains(response, header, value):
    assert header in response.headers, f"Header '{header}' is not part of response headers: {response.headers}"
    assert value in response.headers[header], f"Header '{header}' does not contain '{value}' but '{response.headers[header]}'"

def assert_response_body_contains(response, text):
    assert text in response.text, f"Test '{text}' is not part of response body: {response.text}"