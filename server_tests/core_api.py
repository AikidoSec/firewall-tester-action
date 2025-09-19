import requests
import json
import time
import os


class CoreApi:
    def __init__(self, token: str, core_url: str, test_name: str, config_update_delay: int = 60):
        self.token = token
        self.core_url = core_url
        self.test_name = test_name
        self.config_update_delay = config_update_delay

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
        time.sleep(self.config_update_delay)
        return response.json()

    def update_runtime_config_file(self, config_file: str) -> dict:
        with open(self.get_full_path(config_file), "r") as f:
            config = json.load(f)
        return self.update_runtime_config_json(config)

    def update_runtime_firewall_json(self, firewall: dict) -> dict:
        response = requests.post(f"{self.core_url}/api/runtime/firewall/lists",
                                 headers={"Authorization": f"{self.token}"}, json=firewall)
        time.sleep(self.config_update_delay)
        return response.json()

    def update_runtime_firewall_file(self, file_name: str) -> dict:
        with open(self.get_full_path(file_name), "r") as f:
            firewall = json.load(f)
        return self.update_runtime_firewall_json(firewall)

    def get_events(self, filter_type: str = None) -> list:
        response = requests.get(
            f"{self.core_url}/api/runtime/events", headers={"Authorization": f"{self.token}"})
        events = response.json()
        if filter_type:
            events = [event for event in events if event['type'] == filter_type]
        return events

    def wait_for_new_events(self, max_wait_time: int, old_events_length: int):
        while max_wait_time > 0:
            if len(self.get_events()) > old_events_length:
                return True
            time.sleep(1)
            max_wait_time -= 1
        return False
