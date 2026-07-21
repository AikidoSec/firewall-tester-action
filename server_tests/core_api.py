import requests
import json
import time
import os


CONFIG_PROPAGATION_DELAY_SECONDS = 1
CONFIG_UPDATE_DELAY_SECONDS = int(os.environ.get("CONFIG_UPDATE_DELAY", "60"))


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
        time.sleep(CONFIG_UPDATE_DELAY_SECONDS)
        return response.json()

    def wait_for_config_delivery(self, timeout_seconds: float) -> dict:
        deadline = time.monotonic() + timeout_seconds
        last_error = None

        while time.monotonic() < deadline:
            remaining_seconds = deadline - time.monotonic()
            try:
                response = requests.get(
                    f"{self.core_url}/api/runtime/config/delivery",
                    headers={"Authorization": f"{self.token}"},
                    timeout=min(5, max(0.1, remaining_seconds)),
                )
                response.raise_for_status()
                delivery = response.json()
                if delivery["deliveredConfigUpdatedAt"] >= delivery["configUpdatedAt"]:
                    time.sleep(CONFIG_PROPAGATION_DELAY_SECONDS)
                    return delivery
            except (requests.RequestException, ValueError, KeyError) as error:
                last_error = error
            time.sleep(0.25)

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
        time.sleep(CONFIG_UPDATE_DELAY_SECONDS)
        return response.json()

    def update_runtime_firewall_file(self, file_name: str) -> dict:
        with open(self.get_full_path(file_name), "r", encoding="utf-8") as f:
            firewall = json.load(f)
        return self.update_runtime_firewall_json(firewall)

    def get_events(self, filter_type: str = None) -> list:
        response = requests.get(
            f"{self.core_url}/api/runtime/events", headers={"Authorization": f"{self.token}"})
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

    def wait_for_heartbeat_after(self, max_wait_time: int, old_events_length: int,
                                 not_before_ms: int, max_heartbeats: int = 2):
        """Prefer a post-traffic heartbeat, falling back to content validation."""
        deadline = time.monotonic() + max_wait_time
        checked = 0
        candidates = []

        while time.monotonic() < deadline:
            candidates = self.get_events("heartbeat")[
                old_events_length:old_events_length + max_heartbeats
            ]

            while checked < len(candidates):
                heartbeat = candidates[checked]
                checked += 1
                ended_at = heartbeat.get("stats", {}).get("endedAt", 0)
                if ended_at >= not_before_ms:
                    return heartbeat, candidates

            if checked >= max_heartbeats:
                break

            time.sleep(1)

        return (candidates[-1] if candidates else None), candidates

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
