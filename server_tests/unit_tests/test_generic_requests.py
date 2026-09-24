import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import requests


SERVER_TESTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER_TESTS))
import testlib

spec = importlib.util.spec_from_file_location(
    "generic_test", SERVER_TESTS / "test-demo-apps-generic-tests" / "test.py")
generic_test = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generic_test)


def response(status, body="[]"):
    result = requests.Response()
    result.status_code = status
    result._content = body.encode()
    result.read = lambda: result.content
    return result


class GenericRequestsTest(unittest.TestCase):
    def run_generic_test(self, missing_response_index=None, pets_status=200, pets_body="[]"):
        sent = []
        server = testlib.TestServer(12345, "unused")

        def send(request, **kwargs):
            if request.method == "POST":
                sent.append(request)
                if len(sent) == missing_response_index:
                    return response(None)
                return response(200 if len(sent) == 1 else 500)
            if "googlebot" in request.headers.get("User-Agent", ""):
                return response(403)
            return response(pets_status, pets_body)

        def get_raw(route, headers):
            return response(403 if headers["user"] == "789" else 200)

        with patch.object(server, "get_raw", side_effect=get_raw), \
                patch("requests.sessions.Session.send", side_effect=send), \
                patch("testlib.time.sleep"):
            generic_test.run_test(server, None)
        return sent

    def test_deep_json_reaches_transport_without_recursive_encoding(self):
        recursion_limit = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(1000)
            # Exercise recursion limits even when the C encoder accepts deeper payloads.
            with patch("json.encoder.c_make_encoder", None):
                sent = self.run_generic_test()
        finally:
            sys.setrecursionlimit(recursion_limit)
        self.assertEqual(len(sent), 5)
        body = sent[2].body
        if isinstance(body, bytes):
            body = body.decode()
        self.assertEqual(sent[2].headers["Content-Type"], "application/json")
        self.assertTrue(body.startswith('{"a":{"key8000":{"key7999":'))
        self.assertEqual(body.count('"key'), 8000)
        self.assertIn('"key1":{"a":"b"}', body)
        self.assertTrue(body.endswith(',"name":"Malicious Pet\', \'Gru from the Minions\') --"}'))
        self.assertEqual(json.loads(sent[0].body)["name"], "test")
        self.assertEqual(json.loads(sent[1].body)["name"], "Malicious Pet', 'Gru from the Minions') --")

    def test_missing_deep_attack_response_fails(self):
        for index in (3, 4, 5):
            with self.subTest(index=index):
                with self.assertRaisesRegex(AssertionError, "No HTTP response"):
                    self.run_generic_test(missing_response_index=index)

    def test_failed_database_read_cannot_pass_as_an_absent_attack(self):
        with self.assertRaisesRegex(AssertionError, "3 assertion.*failed"):
            self.run_generic_test(pets_status=500, pets_body='relation "Pets" does not exist')

    def test_successful_injection_is_still_detected(self):
        with self.assertRaisesRegex(AssertionError, "Bypass for big nested json"):
            self.run_generic_test(pets_body='[{"owner":"Gru from the Minions"}]')

    def test_exhausted_raw_post_retries_fail_the_assertion(self):
        server = testlib.TestServer(12345, "unused")
        collector = testlib.AssertionCollector()
        with patch("requests.sessions.Session.send", side_effect=requests.ConnectionError("unreachable")), \
                patch("testlib.time.sleep"), patch("builtins.print"):
            result = server.post_raw("/api/create", data="{}")
        generic_test.check_pets_after_attack(collector, server, result, "big nested json")
        with self.assertRaisesRegex(AssertionError, "No HTTP response for big nested json"):
            collector.raise_if_failures()


if __name__ == "__main__":
    unittest.main()
