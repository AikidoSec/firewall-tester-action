import requests
import time
import sys
from testlib import *
from core_api import CoreApi
import os


def run_test(port: int, token: str, config_update_delay: int):
    pass


if __name__ == "__main__":
    args = load_test_args()
    run_test(args.server_port, args.token, args.config_update_delay)
