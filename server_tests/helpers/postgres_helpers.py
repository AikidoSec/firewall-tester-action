import subprocess
import time

from helpers.docker_helpers import docker_ostype, remove_container


if docker_ostype() == "linux":
    POSTGRES_IMAGE = "postgres"
    POSTGRES_USER = "myuser"
    POSTGRES_PASSWORD = "mysecretpassword"
else:
    POSTGRES_IMAGE = "sokigo/postgresql-windows:15.15-2022"
    POSTGRES_USER = "postgres"
    POSTGRES_PASSWORD = "postgres"


def start_postgres(network_name: str, postgres_host: str) -> None:
    docker_args = [
        "docker", "run", "--rm", "--name", "postgres",
        "--network", network_name, "--ip", postgres_host,
        "-e", f"POSTGRES_USER={POSTGRES_USER}",
        "-e", f"POSTGRES_PASSWORD={POSTGRES_PASSWORD}",
        "-e", "POSTGRES_DB=mydb",
        "-p", "5432:5432",
        "-d", POSTGRES_IMAGE
    ]

    subprocess.run(docker_args, check=True)
    print("Started Postgres container")
    wait_for_postgres_ready()


def wait_for_postgres_ready(timeout_seconds: int = 180) -> None:
    ready_command = ["docker", "exec", "postgres", "pg_isready", "-U", POSTGRES_USER, "-h", "127.0.0.1", "-p", "5432"]

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = subprocess.run(
            ready_command,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return
        time.sleep(1)

    raise RuntimeError(
        f"Postgres did not become ready after {timeout_seconds} seconds"
    )


def stop_postgres() -> None:
    remove_container("postgres")


def create_test_database(db_name: str) -> None:
    create_database_command = ["docker", "exec", "-e", f"PGPASSWORD={POSTGRES_PASSWORD}", "postgres", "createdb",
                               "-w", "-h", "127.0.0.1", "-p", "5432", "-U", POSTGRES_USER, db_name]
    subprocess.run(create_database_command, check=True)
