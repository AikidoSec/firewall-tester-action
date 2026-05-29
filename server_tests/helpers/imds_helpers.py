import ipaddress

from helpers.docker_helpers import (
    connect_target_to_network,
    container_running,
    create_network,
    disconnect_target_from_network,
    is_windows_container_mode,
    network_exists,
    remove_network,
    start_mock_http_server_on_network,
    stop_mock_http_server_on_network,
    wait_for_container_tcp,
)


IMDS_SPECS = [
    {
        "ip": "169.254.169.254",
        "subnet": "169.254.169.248/29",
        "gateway": "169.254.169.249",
        "network": "firewall-tester-action-imds-169",
        "container": "firewall-tester-action-imds-169",
    },
    {
        "ip": "100.100.100.200",
        "subnet": "100.100.100.192/28",
        "gateway": "100.100.100.193",
        "network": "firewall-tester-action-imds-100",
        "container": "firewall-tester-action-imds-100",
    },
    {
        "ip": "fd00:ec2::254",
        "subnet": "fd00:ec2::/64",
        "gateway": "fd00:ec2::1",
        "network": "firewall-tester-action-imds-v6",
        "container": "firewall-tester-action-imds-v6",
    },
]

def _is_ipv6_spec(spec: dict) -> bool:
    return ipaddress.ip_address(spec["ip"]).version == 6


def _enabled_imds_specs():
    for spec in IMDS_SPECS:
        if is_windows_container_mode() and _is_ipv6_spec(spec):
            continue
        yield spec


def start_mock_imds_servers():
    for spec in _enabled_imds_specs():
        if not network_exists(spec["network"]):
            create_network(spec["network"], spec["subnet"], gateway=spec["gateway"], internal=True)

        if not container_running(spec["container"]):
            stop_mock_http_server_on_network(spec["container"])
            start_mock_http_server_on_network(
                spec["container"],
                spec["network"],
                spec["ip"],
            )

        host = "::1" if _is_ipv6_spec(spec) else "127.0.0.1"
        wait_for_container_tcp(spec["container"], host, 80, timeout_seconds=60)


def stop_mock_imds_servers():
    for spec in IMDS_SPECS:
        stop_mock_http_server_on_network(spec["container"])
    for spec in IMDS_SPECS:
        remove_network(spec["network"])


def connect_target_to_mock_imds_servers(target_container_name: str):
    for spec in _enabled_imds_specs():
        connect_target_to_network(target_container_name, spec["network"])


def disconnect_target_from_mock_imds_servers(target_container_name: str):
    for spec in IMDS_SPECS:
        disconnect_target_from_network(target_container_name, spec["network"])
