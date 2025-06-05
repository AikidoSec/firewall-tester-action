import requests

class CoreApi:
  def __init__(self, token: str):
    self.token = token

  @classmethod
  def get_app_token(cls, core_url: str) -> str:
    response = requests.post(f"{core_url}/api/runtime/apps")
    return response.json()["token"]

  def get_runtime_config(self, core_url: str) -> dict:
    response = requests.get(f"{core_url}/api/runtime/config", headers={"Authorization": f"{self.token}"})
    return response.json()

  def update_runtime_config(self, core_url: str, config: dict) -> dict:
    response = requests.post(f"{core_url}/api/runtime/config", headers={"Authorization": f"{self.token}"}, json=config)
    return response.json()

  