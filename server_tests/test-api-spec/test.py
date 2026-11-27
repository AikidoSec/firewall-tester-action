import json

from testlib import *
from core_api import CoreApi

'''
1. Sets up a simple config.
2. Sends one post request.
3. Waits for the heartbeat event and validates the API schema reporting.
'''


def get_api_spec_with_body():
    url = "/api/create?name=test2&url_age=100"
    body = {
        "name": "test2",
        "age": 34
    }
    headers = {
        "Content-Type": "application/json",
    }
    return url, body, headers


def get_api_spec_simple():
    url = "/api/create?userId=12345&color=red"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer your_token_here"
    }
    body = {
        "name": "test3",
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
            "provider": "Visa",
            "cardNumber": "4111111111111111",
            "expiryDate": "12/25"
        },
        "total": 79.97
    }
    return url, body, headers


def run_test(s: TestServer, c: CoreApi):
    with open(c.get_full_path("expect_api_spec.json"), encoding="utf-8") as file:
        expected_report = json.load(file)
    assert expected_report, "Expected heartbeat fixture expect_api_spec.json is empty"
    check_reported_schema(s, c, expected_report)


@with_heartbeats
def check_reported_schema(s, c, expected_report, collector, heartbeats):
    # Keep both requests in the same heartbeat so their schemas can be merged.
    heartbeats.wait_for_next_interval()
    collector.raise_if_failures()

    for request in (get_api_spec_with_body(), get_api_spec_simple()):
        response = s.post(*request)
        collector.soft_assert_response_code_is(response, 200)

    heartbeats.wait_for_entries([expected_report])


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
