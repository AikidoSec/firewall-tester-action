import requests
import json
import time
import os
from collections import Counter


CONFIG_PROPAGATION_DELAY_SECONDS = int(os.environ.get("CONFIG_PROPAGATION_DELAY", "1"))
HEARTBEAT_TIMEOUT_SECONDS = 160


class CoreApi:
    def __init__(self, token: str, core_url: str, test_name: str):
        self.token = token
        self.core_url = core_url
        self.test_name = test_name

    @classmethod
    def get_app_token(cls, core_url: str) -> str:
        response = requests.post(f"{core_url}/api/runtime/apps")
        return response.json()["token"]

    def get_full_path(self, file_name: str) -> str:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), self.test_name, file_name)

    def get_runtime_config(self) -> dict:
        response = requests.get(
            f"{self.core_url}/api/runtime/config", headers={"Authorization": f"{self.token}"})
        return response.json()

    def update_runtime_config_json(self, config: dict) -> dict:
        response = requests.post(f"{self.core_url}/api/runtime/config",
                                 headers={"Authorization": f"{self.token}"}, json=config)
        response.raise_for_status()
        self.wait_for_config_delivery()
        return response.json()

    def wait_for_config_delivery(self, timeout_seconds: float = 120) -> dict:
        deadline = time.monotonic() + timeout_seconds
        last_error = None

        while time.monotonic() < deadline:
            try:
                response = requests.get(
                    f"{self.core_url}/api/runtime/config/delivery",
                    headers={"Authorization": f"{self.token}"},
                    timeout=10,
                )
                response.raise_for_status()
                delivery = response.json()
                if delivery["deliveredConfigUpdatedAt"] >= delivery["configUpdatedAt"]:
                    time.sleep(CONFIG_PROPAGATION_DELAY_SECONDS)
                    return delivery
            except (requests.RequestException, ValueError, KeyError) as error:
                last_error = error
            time.sleep(1)

        raise TimeoutError(
            f"Agent did not fetch firewall lists for its current runtime "
            f"configuration within {timeout_seconds}s: {last_error}"
        )

    def update_runtime_config_file(self, config_file: str) -> dict:
        with open(self.get_full_path(config_file), "r", encoding="utf-8") as f:
            config = json.load(f)
        return self.update_runtime_config_json(config)

    def update_runtime_firewall_json(self, firewall: dict) -> dict:
        response = requests.post(f"{self.core_url}/api/runtime/firewall/lists",
                                 headers={"Authorization": f"{self.token}"}, json=firewall)
        response.raise_for_status()
        self.wait_for_config_delivery()
        return response.json()

    def update_runtime_firewall_file(self, file_name: str) -> dict:
        with open(self.get_full_path(file_name), "r", encoding="utf-8") as f:
            firewall = json.load(f)
        return self.update_runtime_firewall_json(firewall)

    def get_events(self, filter_type: str = None, include_headers: bool = False, *, timeout=None) -> list:
        response = requests.get(
            f"{self.core_url}/api/runtime/events",
            headers={"Authorization": f"{self.token}"},
            params={"includeHeaders": "true"} if include_headers else None,
            timeout=timeout,
        )
        events = response.json()
        if filter_type:
            events = [event for event in events if event['type'] == filter_type]
        return events

    def wait_for_new_events(self, max_wait_time: int, old_events_length: int, filter_type: str = None):
        while max_wait_time > 0:
            if len(self.get_events(filter_type)) > old_events_length:
                return True
            time.sleep(1)
            max_wait_time -= 1
        return False

    def track_heartbeats(self, collector, *, include_startup=False):
        return Heartbeats(self, collector, include_startup)

    def set_mock_server_down(self):
        response = requests.post(
            f"{self.core_url}/api/runtime/apps/down", headers={"Authorization": f"{self.token}"})
        return response.json()

    def set_mock_server_up(self):
        response = requests.post(
            f"{self.core_url}/api/runtime/apps/up", headers={"Authorization": f"{self.token}"})
        return response.json()

    def set_mock_server_timeout(self):
        response = requests.post(
            f"{self.core_url}/api/runtime/apps/timeout", headers={"Authorization": f"{self.token}"})
        return response.json()


class Heartbeats:
    def __init__(self, core, collector, include_startup):
        self.core = core
        self.collector = collector
        self._all_reports = [] if include_startup else core.get_events("heartbeat")
        self._start_index = len(self._all_reports)

    @property
    def _reports(self):
        return self._all_reports[self._start_index:]

    def read(self, *, timeout=None):
        self._all_reports = self.core.get_events("heartbeat", timeout=timeout)
        return self._reports

    def _poll_reports(self):
        not_before_ms = int(time.time() * 1000)
        deadline = time.monotonic() + HEARTBEAT_TIMEOUT_SECONDS
        previous_count = 0
        while (remaining := deadline - time.monotonic()) > 0:
            try:
                reports = self.read(timeout=remaining)
            except requests.Timeout:
                break
            if len(reports) != previous_count:
                previous_count = len(reports)
                fresh_reports = [report for report in reports if report.get("stats", {}).get("endedAt", 0) >= not_before_ms]
                if fresh_reports:
                    yield fresh_reports
            time.sleep(1)

        self.collector.add_failure(
            f"{self.core.test_name}: heartbeat check timed out after {HEARTBEAT_TIMEOUT_SECONDS}s. "
            f"Received {len(self._reports)} report(s): {json.dumps(self._reports)}"
        )

    def wait_for_next_report(self):
        next(self._poll_reports(), None)
        return self._reports

    def entries(self, field):
        return [entry for report in self._reports for entry in (report.get(field) or [])]

    def wait_for_entries(self, expected, *, field=None, key=None):
        from testlib import assert_event_contains_subset

        def missing(entries):
            if key is not None:
                return set(expected).difference(map(key, entries))
            return [
                item for item in expected
                if not any(assert_event_contains_subset(entry, item, dry_mode=True) for entry in entries)
            ]

        entries = []
        for fresh_reports in self._poll_reports():
            entries = self.entries(field) if field is not None else fresh_reports
            if not missing(entries):
                return entries

        if field is not None:
            entries = self.entries(field)
        absent = missing(entries)
        self.collector.soft_assert(not absent, f"Missing heartbeat {field or 'reports'}: {absent}")
        return entries

    def wait_for_totals(self, category, field, expected, *, allow_extra=True):
        def totals():
            result = Counter()
            for report in self._reports:
                counters = report.get("stats", {}).get(category, {}).get(field)
                if isinstance(counters, dict):
                    result.update(counters)
            return result

        target = Counter(expected)
        for _ in self._poll_reports():
            if totals() >= target:
                break
        observed = dict(totals())
        actual = {name: observed.get(name, 0) for name in expected} if allow_extra else observed
        self.collector.soft_assert(actual == expected, f"Expected {category}.{field} counts {expected}, got {observed}")

    def requests_since_startup(self):
        return sum(report.get("stats", {}).get("requests", {}).get("total", 0) for report in self._all_reports)

    def attacks_detected(self):
        return sum(report["stats"]["requests"]["attacksDetected"]["total"] for report in self._reports)
