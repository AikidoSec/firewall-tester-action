import json
import ipaddress
import os
import subprocess
import sys
import time


WINDOWS_PYTHON_IMAGE = "mcr.microsoft.com/windows-cssc/python:3.13-nanoserver-ltsc2022"
LINUX_PYTHON_IMAGE = "python:3.13-slim"
HELPERS_DIR = os.path.dirname(os.path.abspath(__file__))


_DOCKER_OSTYPE_CACHE = None


def _docker_ostype_from_runner() -> str | None:
    runner_os = os.environ.get("RUNNER_OS", "").strip().lower()
    return runner_os if runner_os in {"linux", "windows"} else None


def _docker_ostype_from_docker() -> str:
    commands = [
        ["docker", "version", "--format", "{{.Server.Os}}"],
        ["docker", "info", "--format", "{{.OSType}}"],
    ]

    for command in commands:
        try:
            result = _run_command(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError:
            continue

        ostype = result.stdout.strip().lower()
        if ostype in {"linux", "windows"}:
            return ostype

    raise RuntimeError("Could not detect Docker OS type")


def docker_ostype() -> str:
    global _DOCKER_OSTYPE_CACHE
    if _DOCKER_OSTYPE_CACHE is None:
        _DOCKER_OSTYPE_CACHE = _docker_ostype_from_runner() or _docker_ostype_from_docker()
    return _DOCKER_OSTYPE_CACHE


def is_windows_container_mode() -> bool:
    return docker_ostype() == "windows"


def docker_network_driver() -> str:
    return "nat" if is_windows_container_mode() else "bridge"


def python_image() -> str:
    return WINDOWS_PYTHON_IMAGE if is_windows_container_mode() else LINUX_PYTHON_IMAGE


def container_running(container_name: str) -> bool:
    result = _run_command(
        ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip().lower() == "true"


def wait_for_running_container(container_name: str, timeout_seconds: int = 20):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if container_running(container_name):
            return
        time.sleep(1)
    raise Exception(f"Container {container_name} did not start after {timeout_seconds} seconds")


def container_exists(container_name: str) -> bool:
    return _run_command(
        ["docker", "inspect", container_name],
        capture_output=True,
        text=True,
    ).returncode == 0


def remove_container(container_name: str):
    _run_command(
        ["docker", "rm", "-f", container_name],
        capture_output=True,
    )


def network_exists(network_name: str) -> bool:
    return _run_command(
        ["docker", "network", "inspect", network_name],
        capture_output=True,
        text=True,
    ).returncode == 0


def _run_command(
    command: list[str],
    check: bool = False,
    capture_output: bool = False,
    text: bool = False,
    input: str | None = None,
    attempts: int = 5,
    delay_seconds: int = 3,
) -> subprocess.CompletedProcess:
    for attempt in range(1, attempts + 1):
        result = subprocess.run(
            command,
            capture_output=capture_output,
            text=text,
            input=input,
        )
        if result.returncode == 0 or not check:
            return result

        if attempt == attempts:
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, end="", file=sys.stderr)
            result.check_returncode()

        print(
            f"Command failed "
            f"(attempt {attempt}/{attempts}); retrying in {delay_seconds}s"
        )
        time.sleep(delay_seconds)

    return result


def wait_for_docker_ready():
    global _DOCKER_OSTYPE_CACHE

    result = _run_command(
        ["docker", "version", "--format", "{{.Server.Os}}"],
        check=True,
        capture_output=True,
        text=True,
        attempts=24,
        delay_seconds=5,
    )
    docker_os = result.stdout.strip().lower()
    runner_os = _docker_ostype_from_runner()
    if runner_os is not None and docker_os != runner_os:
        raise RuntimeError(f"Docker is running in {docker_os} mode, expected {runner_os}")
    if docker_os not in {"linux", "windows"}:
        raise RuntimeError(f"Could not detect Docker OS type: {docker_os}")
    _DOCKER_OSTYPE_CACHE = docker_os


def create_network(network_name: str, subnet: str, gateway: str):
    network = ipaddress.ip_network(subnet, strict=False)
    if is_windows_container_mode() and network.version == 6:
        raise RuntimeError("IPv6 Docker networks are not supported on Windows")

    ipv6_args = ["--ipv6"] if network.version == 6 else []
    command = [
        "docker",
        "network",
        "create",
        "--driver",
        docker_network_driver(),
        "--subnet",
        subnet,
        "--gateway",
        gateway,
        *ipv6_args,
        network_name,
    ]
    _run_command(command, check=True, capture_output=True, text=True)


def remove_network(network_name: str):
    _run_command(
        ["docker", "network", "rm", network_name],
        capture_output=True,
    )


def target_connected_to_network(target_container_name: str, network_name: str) -> bool:
    result = _run_command(
        ["docker", "inspect", "-f", "{{json .NetworkSettings.Networks}}", target_container_name],
        capture_output=True,
        text=True,
        check=True,
    )
    networks = json.loads(result.stdout)
    return network_name in networks


def connect_target_to_network(target_container_name: str, network_name: str):
    if target_connected_to_network(target_container_name, network_name):
        return
    _run_command(["docker", "network", "connect", network_name, target_container_name], check=True)


def disconnect_target_from_network(target_container_name: str, network_name: str):
    _run_command(
        ["docker", "network", "disconnect", network_name, target_container_name],
        capture_output=True,
    )


def wait_for_container_tcp(
    container_name: str,
    host: str,
    port: int,
    timeout_seconds: int = 30,
):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = _run_command(
            [
                "docker",
                "exec",
                container_name,
                "python",
                "-c",
                f"import socket; socket.create_connection(({host!r}, {port}), 1).close()",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return
        time.sleep(1)
    raise Exception(f"Container {container_name} did not accept TCP connections on {host}:{port}")


def mock_http_server_mount() -> tuple[str, str]:
    if is_windows_container_mode():
        return f"{HELPERS_DIR}:C:\\test-helpers:ro", "C:\\test-helpers\\mock_http_server.py"
    return f"{HELPERS_DIR}:/test-helpers:ro", "/test-helpers/mock_http_server.py"


def start_mock_http_server_on_network(
    container_name: str,
    network_name: str,
    ip: str,
):
    volume_mount, server_path = mock_http_server_mount()
    address = ipaddress.ip_address(ip)
    ip_args = ["--ip6", ip] if address.version == 6 else ["--ip", ip]
    bind_args = ["-e", "BIND_HOST=::"] if address.version == 6 else []
    command = [
        "docker",
        "run",
        "-d",
        "--name",
        container_name,
        "--network",
        network_name,
        *ip_args,
        *bind_args,
        "-v",
        volume_mount,
        python_image(),
        "python",
        server_path,
    ]
    _run_command(command, check=True)
    wait_for_running_container(container_name, timeout_seconds=60)
    host = "::1" if address.version == 6 else "127.0.0.1"
    wait_for_container_tcp(container_name, host, 80, timeout_seconds=60)


def stop_mock_http_server_on_network(container_name: str):
    remove_container(container_name)


def _target_loopback_mock_container_name(target_container_name: str, port: int) -> str:
    return f"{target_container_name}-mock-{port}"


def start_mock_http_server_on_target_loopback(target_container_name: str, port: int = 4000):
    container_name = _target_loopback_mock_container_name(target_container_name, port)
    remove_container(container_name)
    volume_mount, server_path = mock_http_server_mount()
    command = [
        "docker",
        "run",
        "-d",
        "--name",
        container_name,
        "--network",
        f"container:{target_container_name}",
        "-e",
        f"PORT={port}",
        "-e",
        "BIND_HOST=127.0.0.1",
        "-v",
        volume_mount,
        python_image(),
        "python",
        server_path,
    ]
    _run_command(command, check=True)
    wait_for_running_container(container_name, timeout_seconds=60)
    wait_for_container_tcp(container_name, "127.0.0.1", port, timeout_seconds=60)


def stop_mock_http_server_on_target_loopback(target_container_name: str, port: int = 4000):
    remove_container(_target_loopback_mock_container_name(target_container_name, port))


def get_hosts_file(target_container_name: str) -> str:
    if is_windows_container_mode():
        command = [
            "docker",
            "exec",
            target_container_name,
            "cmd",
            "/S",
            "/C",
            r"type %SystemRoot%\System32\drivers\etc\hosts",
        ]
    else:
        command = [
            "docker",
            "exec",
            "-u",
            "0",
            target_container_name,
            "cat",
            "/etc/hosts",
        ]

    return _run_command(command, check=True, capture_output=True, text=True).stdout


def set_hosts_file(target_container_name: str, contents: str):
    if is_windows_container_mode():
        command = [
            "docker",
            "exec",
            "-i",
            target_container_name,
            "cmd",
            "/S",
            "/C",
            r"more > %SystemRoot%\System32\drivers\etc\hosts",
        ]
    else:
        command = [
            "docker",
            "exec",
            "-i",
            "-u",
            "0",
            target_container_name,
            "sh",
            "-c",
            "cat > /etc/hosts",
        ]

    _run_command(command, check=True, capture_output=True, text=True, input=contents)


def append_hosts_entry(target_container_name: str, ip: str, hostname: str):
    entry = f"\n{ip} {hostname}\n"
    if is_windows_container_mode():
        command = [
            "docker",
            "exec",
            "-i",
            target_container_name,
            "cmd",
            "/S",
            "/C",
            r"more >> %SystemRoot%\System32\drivers\etc\hosts",
        ]
    else:
        command = [
            "docker",
            "exec",
            "-i",
            "-u",
            "0",
            target_container_name,
            "sh",
            "-c",
            "cat >> /etc/hosts",
        ]

    _run_command(command, check=True, capture_output=True, text=True, input=entry)
