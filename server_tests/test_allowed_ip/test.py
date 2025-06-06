import requests
import time
import sys
from testlib import *
from core_api import CoreApi
import os
'''
1. Sets up the allowed IP address config for route '/test'. Checks that requests are blocked.
2. Changes the config to remote the allowed IP address. Checks that requests are passing.
3. Changes the config again to enable allowed IP address. Checks that requests are blocked.
'''


def run_test(port: int, token: str):
    s = TestServer(port=port, token=token)
    c = CoreApi(token=token, core_url=f"http://localhost:3000")
    response = s.get("/somethingVerySpecific")
    
    assert_response_code_is(response, 403)
    assert_response_header_contains(response, "Content-Type", "text")
    assert_response_body_contains(response, "not allowed")

    c.update_runtime_config_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "change_config_remove_allowed_ip.json"))
        
    response = s.get("/somethingVerySpecific")
    assert_response_code_is(response, 200)
    assert_response_body_contains(response, "Hello")
    
    c.update_runtime_config_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "start_config.json"))
        
    response = s.get("/somethingVerySpecific")
    assert_response_code_is(response, 403)
    assert_response_header_contains(response, "Content-Type", "text")
    assert_response_body_contains(response, "not allowed")

    c.update_runtime_config_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_allow_private.json"))
    response = s.get("/somethingVerySpecific")
    assert_response_code_is(response, 200)
    assert_response_body_contains(response, "Hello")
    
    
if __name__ == "__main__":
    args = load_test_args()
    run_test(args.server_port, args.token)