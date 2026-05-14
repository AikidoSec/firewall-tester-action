import requests
import time
import sys
from testlib import *
from core_api import CoreApi

'''
Tests SQL injection detection via multipart/form-data and application/x-www-form-urlencoded,
including known bypass techniques:

1. Baseline: standard multipart/form-data POST is blocked
2. Baseline: standard URL-encoded form POST is blocked
3. JSON prefix {} before multipart boundary data
4. Variant: JSON array prefix [] before multipart boundary data
5. Variant: JSON prefix with extra whitespace/newlines
6. Duplicate boundary parameter (Rack CVE-style): boundary=safe; boundary=real
7. Content-Type with extra parameters (charset)
'''

SQLI_PAYLOAD = "Malicious Pet', 'Gru from the Minions') --"
BOUNDARY = "WebKitFormBoundary7MA4YWxkTrZu0gW"


def build_multipart_body(field_name, field_value, boundary=BOUNDARY):
    """Build a standard multipart/form-data body."""
    body = f"--{boundary}\r\n"
    body += f"Content-Disposition: form-data; name=\"{field_name}\"\r\n\r\n"
    body += f"{field_value}\r\n"
    body += f"--{boundary}--\r\n"
    return body.encode("utf-8")


def test_baseline_multipart(collector, s):
    """Standard multipart/form-data SQL injection should be blocked."""
    body = build_multipart_body("name", SQLI_PAYLOAD)
    headers = {
        "Content-Type": f"multipart/form-data; boundary={BOUNDARY}"
    }
    response = s.post_raw("/api/create-form", body=body, headers=headers)
    collector.soft_assert_response_code_is_not(
        response, 200,
        "Baseline multipart form-data SQL injection must not succeed (got 200)")


def test_baseline_urlencoded(collector, s):
    """Standard URL-encoded form SQL injection should be blocked."""
    body = f"name={SQLI_PAYLOAD}".encode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = s.post_raw("/api/create-form", body=body, headers=headers)
    collector.soft_assert_response_code_is_not(
        response, 200,
        "Baseline URL-encoded SQL injection must not succeed (got 200)")


def test_json_prefix_bypass(collector, s):
    """
    Prefix {} before multipart data.
    The backend still processes the multipart payload.
    This should be blocked if the fix is in place.
    """
    multipart_body = build_multipart_body("name", SQLI_PAYLOAD)
    body = b"{}\r\n" + multipart_body
    headers = {
        "Content-Type": f"multipart/form-data; boundary={BOUNDARY}"
    }
    response = s.post_raw("/api/create-form", body=body, headers=headers)
    collector.soft_assert_response_code_is_not(
        response, 200,
        "JSON prefix {} bypass must not succeed (got 200)")


def test_json_array_prefix_bypass(collector, s):
    """Variant: prefix [] (empty JSON array) before multipart data."""
    multipart_body = build_multipart_body("name", SQLI_PAYLOAD)
    body = b"[]\r\n" + multipart_body
    headers = {
        "Content-Type": f"multipart/form-data; boundary={BOUNDARY}"
    }
    response = s.post_raw("/api/create-form", body=body, headers=headers)
    collector.soft_assert_response_code_is_not(
        response, 200,
        "JSON array prefix [] bypass must not succeed (got 200)")


def test_json_prefix_whitespace_bypass(collector, s):
    """Variant: {} with extra whitespace and newlines before multipart data."""
    multipart_body = build_multipart_body("name", SQLI_PAYLOAD)
    body = b"{}\n\n\n" + multipart_body
    headers = {
        "Content-Type": f"multipart/form-data; boundary={BOUNDARY}"
    }
    response = s.post_raw("/api/create-form", body=body, headers=headers)
    collector.soft_assert_response_code_is_not(
        response, 200,
        "JSON prefix with whitespace bypass must not succeed (got 200)")


def test_json_object_with_data_prefix_bypass(collector, s):
    """Variant: {"a":1} (non-empty JSON) before multipart data."""
    multipart_body = build_multipart_body("name", SQLI_PAYLOAD)
    body = b'{"a":1}\r\n' + multipart_body
    headers = {
        "Content-Type": f"multipart/form-data; boundary={BOUNDARY}"
    }
    response = s.post_raw("/api/create-form", body=body, headers=headers)
    collector.soft_assert_response_code_is_not(
        response, 200,
        "Non-empty JSON prefix bypass must not succeed (got 200)")


def test_duplicate_boundary_bypass(collector, s):
    """
    Rack CVE-style: duplicate boundary parameter.
    Content-Type has boundary=safe; boundary=real.
    WAF may use first boundary (safe) while app uses last (real).
    Malicious payload is inside the "real" boundary.
    Safe outcomes: 500 (Zen blocked) or 400 (app failed to parse = payload never executed).
    Unsafe outcome: 200 (payload reached the database unblocked).
    """
    safe_boundary = "safeboundary"
    real_boundary = "realboundary"

    body = f"--{real_boundary}\r\n"
    body += f"Content-Disposition: form-data; name=\"name\"\r\n\r\n"
    body += f"{SQLI_PAYLOAD}\r\n"
    body += f"--{real_boundary}--\r\n"
    body = body.encode("utf-8")

    headers = {
        "Content-Type": f"multipart/form-data; boundary={safe_boundary}; boundary={real_boundary}"
    }
    response = s.post_raw("/api/create-form", body=body, headers=headers)
    collector.soft_assert_response_code_is_not(
        response, 200,
        "Duplicate boundary bypass must not succeed (got 200 = payload reached DB)")


def test_boundary_with_charset(collector, s):
    """Content-Type with extra charset parameter should not confuse parsing."""
    body = build_multipart_body("name", SQLI_PAYLOAD)
    headers = {
        "Content-Type": f"multipart/form-data; boundary={BOUNDARY}; charset=utf-8"
    }
    response = s.post_raw("/api/create-form", body=body, headers=headers)
    collector.soft_assert_response_code_is_not(
        response, 200,
        "Multipart with charset param must not succeed (got 200)")


def test_boundary_with_quotes(collector, s):
    """Boundary value wrapped in quotes — some parsers strip quotes, others don't."""
    body = build_multipart_body("name", SQLI_PAYLOAD)
    headers = {
        "Content-Type": f'multipart/form-data; boundary="{BOUNDARY}"'
    }
    response = s.post_raw("/api/create-form", body=body, headers=headers)
    collector.soft_assert_response_code_is_not(
        response, 200,
        "Multipart with quoted boundary must not succeed (got 200)")


def test_mixed_case_content_type(collector, s):
    """Mixed-case Content-Type header value."""
    body = build_multipart_body("name", SQLI_PAYLOAD)
    headers = {
        "Content-Type": f"Multipart/Form-Data; boundary={BOUNDARY}"
    }
    response = s.post_raw("/api/create-form", body=body, headers=headers)
    collector.soft_assert_response_code_is_not(
        response, 200,
        "Mixed-case content-type must not succeed (got 200)")


def test_content_type_with_leading_whitespace(collector, s):
    """Extra whitespace in Content-Type boundary parameter."""
    body = build_multipart_body("name", SQLI_PAYLOAD)
    headers = {
        "Content-Type": f"multipart/form-data;  boundary={BOUNDARY}"
    }
    response = s.post_raw("/api/create-form", body=body, headers=headers)
    collector.soft_assert_response_code_is_not(
        response, 200,
        "Content-Type with extra whitespace must not succeed (got 200)")


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    # Baseline tests
    test_baseline_multipart(collector, s)
    test_baseline_urlencoded(collector, s)

    # Go-specific JSON prefix bypass (bypass.md)
    test_json_prefix_bypass(collector, s)
    test_json_array_prefix_bypass(collector, s)
    test_json_prefix_whitespace_bypass(collector, s)
    test_json_object_with_data_prefix_bypass(collector, s)

    # Boundary manipulation bypasses
    test_duplicate_boundary_bypass(collector, s)
    test_boundary_with_charset(collector, s)
    test_boundary_with_quotes(collector, s)

    # Content-Type header manipulation
    test_mixed_case_content_type(collector, s)
    test_content_type_with_leading_whitespace(collector, s)

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
