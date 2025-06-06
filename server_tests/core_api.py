import requests
import json
import time
import os
import socket

def replace_variables(config: dict) -> dict:
  for key, value in config.items():
    if isinstance(value, str):
      # machine ip address
      machine_ip = socket.gethostbyname(socket.gethostname())
      config[key] = value.replace("${PRIVATE_IP}", machine_ip)
  return config

class CoreApi:
  def __init__(self, token: str, core_url: str, config_update_delay: int = 60):
    self.token = token
    self.core_url = core_url
    self.config_update_delay = config_update_delay

  @classmethod
  def get_app_token(cls, core_url: str) -> str: 
    response = requests.post(f"{core_url}/api/runtime/apps")
    return response.json()["token"]

  def get_runtime_config(self) -> dict:
    response = requests.get(f"{self.core_url}/api/runtime/config", headers={"Authorization": f"{self.token}"})
    return response.json()

  def update_runtime_config_json(self, config: dict) -> dict:
    config = replace_variables(config)
    response = requests.post(f"{self.core_url}/api/runtime/config", headers={"Authorization": f"{self.token}"}, json=config)
    time.sleep(self.config_update_delay)
    return response.json()
  
  def update_runtime_config_file(self, config_file: str) -> dict:
    with open(config_file, "r") as f:
      config = json.load(f)
    return self.update_runtime_config_json(config)
  