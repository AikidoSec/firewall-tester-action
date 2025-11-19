from testlib import *

"""
This test checks that the wave attack detection works for the following cases:
- Filename
- Directory
- File Extension
- Query

The test sends 16 requests to the server with a different IP address for each attack.
The test then waits for 20 seconds and checks that the event was sent to cloud.

NODE: I didn't add the tests for methods (BDMTHD, ...), because they don't reach the aikido middleware.)
"""


def get_random_filename():
    return random.choice([
        ".addressbook",
        ".atom",
        ".bashrc",
        ".boto",
        ".config",
        ".config.json",
        ".config.xml",
        ".config.yaml",
        ".config.yml",
        ".envrc",
        ".eslintignore",
        ".fbcindex",
        ".forward",
        ".gitattributes",
        ".gitconfig",
        ".gitignore",
        ".gitkeep",
        ".gitlab-ci.yaml",
        ".gitlab-ci.yml",
        ".gitmodules",
    ])


def get_random_directory_name():
    return random.choice([
        ".gem",
        ".git",
        ".github",
        ".gnupg",
        ".gsutil",
        ".hg",
        ".vidalia",
        ".vim",
        ".vmware",
        ".vscode",
        "apache",
        "apache2"
    ])


def get_random_file_extension():
    return random.choice([
        "env",
        "bak",
        "sql",
        "sqlite",
        "sqlite3",
        "db",
        "old",
        "save",
        "orig",
        "sqlitedb",
        "sqlite3db"
    ])


def get_random_query():
    return random.choice([
        "SELECT (CASE WHEN 1=1",
        "SELECT COUNT(1)",
        "SLEEP(1)",
        "WAITFOR DELAY",
        "SELECT LIKE(CHAR(1))",
        "INFORMATION_SCHEMA.COLUMNS",
        "INFORMATION_SCHEMA.TABLES",
        "MD5('test')",
        "DBMS_PIPE.RECEIVE_MESSAGE",
        "SYSIBM.SYSTABLES",
        "RANDOMBLOB(1)",
        "SELECT * FROM pg_sleep(1)",
        "1'='1",
        "PG_SLEEP(1)",
        "UNION ALL SELECT 1",
        "../../etc/passwd",
    ])


def get_random_path_filename():
    return "GET", f"/api/execute/{get_random_filename()}"


def get_random_path_directory():
    return "GET", f"/api/pets/{get_random_directory_name()}/test.txt"


def get_random_path_extension():
    return "GET", f"/api/pets/file.{get_random_file_extension()}"


def get_random_path_query():
    return "GET", f"/api/pets/?path={get_random_query()}"


def check_wave_attack(get_method_path, ip):
    start_events = c.get_events("detected_attack_wave")
    for i in range(16):
        method, path = get_method_path()
        r = s.request(method, path,
                      headers={"X-Forwarded-For": ip})
    c.wait_for_new_events(20, old_events_length=len(
        start_events), filter_type="detected_attack_wave")
    all_events = c.get_events("detected_attack_wave")
    new_events = all_events[len(start_events):]

    assert len(
        new_events) == 1, f"Expected 1 event, got {len(new_events)} (ip: {ip})"
    assert new_events[0][
        "type"] == "detected_attack_wave", f"Expected detected_attack_wave event, got {new_events[0]['type']}"
    assert new_events[0]["request"][
        "ipAddress"] == ip, f"Expected ipAddress {ip}, got {new_events[0]['request']['ipAddress']}"


def run_test(s: TestServer, c: CoreApi):
    check_wave_attack(get_random_path_filename, "2.16.53.5")
    check_wave_attack(get_random_path_directory, "2.16.53.6")
    check_wave_attack(get_random_path_extension, "2.16.53.7")
    check_wave_attack(get_random_path_query, "2.16.53.8")


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
