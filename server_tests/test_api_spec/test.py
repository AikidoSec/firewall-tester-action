import requests
import time
import sys
from testlib import *
from core_api import CoreApi
import os


'''
1. Sets up a simple config.
2. Sends one post request.
3. Waits for the heartbeat event and validates the API schema reporting.
'''


def get_api_spec_with_no_body():
    url = "/api/v1/orders?userId=12345&status=pending"
    headers = {
        "Content-Type": "application/json",
    }
    return url, None, headers


def get_api_spec_simple():
    url = "/api/v1/orders?userId=12345&status=pending"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer your_token_here"
    }
    body = {
        "orderId": "98765",
        "items": [
            {
                "itemId": "abc123",
                "quantity": 2,
                "price": 29.99,
                "details": {
                    "color": "blue",
                    "size": "M"
                }
            },
            {
                "itemId": "def456",
                "quantity": 1,
                "price": 19.99,
                "details": {
                    "color": "red",
                    "size": "L"
                }
            }
        ],
        "shippingAddress": {
            "name": "John Doe",
            "street": "1234 Elm St",
            "city": "Some City",
            "state": "CA",
            "zip": "90210",
            "country": "USA"
        },
        "paymentMethod": {
            "type": "credit_card",
            "provider": "Visa",
            "cardNumber": "4111111111111111",
            "expiryDate": "12/25"
        },
        "total": 79.97
    }
    return url, body, headers


def get_api_spec_merge():
    url = "/api/v1/orders?userId=12345&status=pending&orderId=80"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "abcdef12345"
    }
    body = {
        "orderPlaced": True
    }
    return url, body, headers


def run_api_spec_tests(fns, expected_json, s: TestServer, c: CoreApi):
    start_events = c.get_events()
    for fn in fns:
        response = s.post(*fn())
        assert_response_code_is(response, 200)

    c.wait_for_new_events(70, old_events_length=len(start_events))

    all_events = c.get_events()
    new_events = all_events[len(start_events):]
    assert_events_length_is(new_events, 1)
    assert_started_event_is_valid(all_events[0])

    assert_event_contains_subset_file(new_events[0], expected_json)


def run_test(s: TestServer, c: CoreApi):
    run_api_spec_tests([
        get_api_spec_with_no_body,
        get_api_spec_simple,
        get_api_spec_merge,
    ], "expect_api_spec.json", s, c)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
