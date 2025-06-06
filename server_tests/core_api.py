import requests
import json
import time

class CoreApi:
  def __init__(self, token: str, core_url: str):
    self.token = token
    self.core_url = core_url

  @classmethod
  def get_app_token(cls, core_url: str) -> str: 
    response = requests.post(f"{core_url}/api/runtime/apps")
    return response.json()["token"]

  def get_runtime_config(self) -> dict:
    response = requests.get(f"{self.core_url}/api/runtime/config", headers={"Authorization": f"{self.token}"})
    return response.json()

  def update_runtime_config_json(self, config: dict) -> dict:
    response = requests.post(f"{self.core_url}/api/runtime/config", headers={"Authorization": f"{self.token}"}, json=config)
    time.sleep(200)
    return response.json()
  
  def update_runtime_config_file(self, config_file: str) -> dict:
    with open(config_file, "r") as f:
      config = json.load(f)
    return self.update_runtime_config_json(config)
  