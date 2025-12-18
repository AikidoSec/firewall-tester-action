from testlib import *
import itertools

"""
This test suite validates wave attack detection functionality across multiple scenarios:

Positive Tests (expect detection):
- Filename patterns: Tests detection of suspicious filenames (e.g., .bashrc, .gitconfig)
- Directory patterns: Tests detection of suspicious directory names (e.g., .git, .vscode)
- File Extension patterns: Tests detection of suspicious file extensions (e.g., .env, .sql)
- Query patterns: Tests detection of suspicious query parameters (e.g., SQL injection attempts)
Each positive test sends 16 requests with the same IP address, waits 20 seconds, and verifies
that exactly 1 attack wave event is detected and contains the correct IP and user information.
The tests also validate the samples metadata in the attack event, ensuring that:
  - Samples is a valid JSON string that parses to a list
  - The number of samples matches the expected count (equal to the length of the pattern list)
  - Each sample is a dictionary containing "method" and "url" fields
  - All samples have method "GET"

Negative Tests (expect no detection):
- Same IP retry: Tests that subsequent attacks from an already-detected IP don't trigger
  additional events (sends 16 requests, waits 5 seconds, expects 0 events)
- Sliding window: Tests that 15 requests spaced 10 seconds apart (15 * 10 seconds = 150 seconds > 60 seconds) don't trigger wave detection
  due to sliding window behavior
- Bypass IP: Tests that requests from allowed/bypass IP addresses don't trigger detection
  (sends 15 requests, expects 0 events)

NOTE: Tests for HTTP methods (BDMTHD, etc.) are not included because they don't reach the aikido middleware.
"""

# Initialize iterators for deterministic value selection
filenames = [
    ".addressbook",
    ".atom",
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
    ".gitlab-ci.yml",
    ".gitmodules",
]
_filename_iterator = itertools.cycle(filenames)
directories = [
    ".gem",
    ".git",
    ".github",
    ".gnupg",
    ".gsutil",
    ".hg",
    ".vidalia",
    ".vmware",
    ".vscode",
    "apache",
    "apache2"
]
_directory_iterator = itertools.cycle(directories)

file_extensions = [
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
]
_file_extension_iterator = itertools.cycle(file_extensions)

queries = [
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
    "SELECT * FROM pg_sleep(1)",
    "1'='1",
    "PG_SLEEP(1)",
    "UNION ALL SELECT 1",
    "../../etc/passwd",
]
_query_iterator = itertools.cycle(queries)


def get_filename():
    return next(_filename_iterator)


def get_directory_name():
    return next(_directory_iterator)


def get_file_extension():
    return next(_file_extension_iterator)


def get_query():
    return next(_query_iterator)


def get_random_path_filename():
    return "GET", f"/api/execute/{get_filename()}"


def get_random_path_directory():
    return "GET", f"/api/pets/{get_directory_name()}/test.txt"


def get_random_path_extension():
    return "GET", f"/api/pets/file.{get_file_extension()}"


def get_random_path_query():
    return "GET", f"/api/pets/?path={get_query()}"


def check_wave_attack(get_method_path, ip, user_id, len_samples):
    start_events = c.get_events("detected_attack_wave")
    for i in range(16):
        method, path = get_method_path()
        r = s.request(method, path,
                      headers={"X-Forwarded-For": ip, "user": user_id})
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

    assert "user" in new_events[0][
        "attack"], f"Expected user in attack, got {new_events[0]['attack']}"
    assert "id" in new_events[0]["attack"][
        "user"], f"Expected id in user, got {new_events[0]['attack']['user']}"
    assert new_events[0]["attack"]["user"][
        "id"] == user_id, f"Expected user id {user_id}, got {new_events[0]['attack']['user']['id']}"

    assert "samples" in new_events[0]["attack"]["metadata"], "Samples not found in metadata"
    assert isinstance(new_events[0]["attack"]["metadata"]
                      ["samples"], str), "Samples is not a string"
    samples = new_events[0]["attack"]["metadata"]["samples"]
    try:
        samples = json.loads(samples)
    except json.JSONDecodeError:
        assert False, f"Samples is not a valid JSON string: {samples}"
    # type of samples is list
    assert isinstance(samples, list), "Samples is not a list"
    assert len(
        samples) == len_samples, f"Expected {len_samples} samples, got {len(samples)}"
    for sample in samples:
        assert isinstance(sample, dict), "Sample is not a dictionary"
        assert "method" in sample, "Method not found in sample"
        assert "url" in sample, "Url not found in sample"
        assert sample["method"] == "GET", f"Method is not GET, got {sample['method']}"
        assert isinstance(sample["url"], str), "Url is not a string"


def check_wave_attack_with_same_ip(get_method_path, ip, user_id):
    start_events = c.get_events("detected_attack_wave")
    for i in range(16):
        method, path = get_method_path()
        r = s.request(method, path,
                      headers={"X-Forwarded-For": ip, "user": user_id})
    c.wait_for_new_events(5, old_events_length=len(
        start_events), filter_type="detected_attack_wave")
    all_events = c.get_events("detected_attack_wave")
    new_events = all_events[len(start_events):]

    assert len(
        new_events) == 0, f"Expected 0 events, got {len(new_events)} (ip: {ip})"


def check_wave_attack_with_same_ip_sliding_window_and_LRU(ip, user_id):
    start_events = c.get_events("detected_attack_wave")
    for _ in range(14):
        time.sleep(1)
        method, path = get_random_path_filename()
        _ = s.request(method, path,
                      headers={"X-Forwarded-For": ip, "user": user_id})
    time.sleep(60)
    # send 1 more request
    method, path = get_random_path_filename()
    _ = s.request(method, path,
                  headers={"X-Forwarded-For": ip, "user": user_id})
    c.wait_for_new_events(10, old_events_length=len(
        start_events), filter_type="detected_attack_wave")
    all_events = c.get_events("detected_attack_wave")
    new_events = all_events[len(start_events):]
    assert len(
        new_events) == 0, f"Test sent 14 suspicious requests with 1 second sleep between each request (same IP) and 1 more request after 60 seconds. Expected 0 attack wave events, but got {len(new_events)} event(s)"


def check_wave_attack_with_bypass_ip(ip, user_id):
    start_events = c.get_events("detected_attack_wave")
    for _ in range(15):
        method, path = get_random_path_filename()
        _ = s.request(method, path,
                      headers={"X-Forwarded-For": ip, "user": user_id})
    c.wait_for_new_events(10, old_events_length=len(
        start_events), filter_type="detected_attack_wave")
    all_events = c.get_events("detected_attack_wave")
    new_events = all_events[len(start_events):]
    assert len(
        new_events) == 0, f"Test sent 15 suspicious requests with bypass IP {ip} (allowedIPAddresses). Expected 0 attack wave events, but got {len(new_events)} event(s)"


def run_test(s: TestServer, c: CoreApi):
    check_wave_attack(get_random_path_filename,
                      "2.16.53.5", "1234", len(filenames))
    check_wave_attack(get_random_path_directory,
                      "2.16.53.6", "1235", len(directories))
    check_wave_attack(get_random_path_extension, "2.16.53.7",
                      "1236", len(file_extensions))
    check_wave_attack(get_random_path_query, "2.16.53.8", "1237", len(queries))

    check_wave_attack_with_same_ip(
        get_random_path_filename, "2.16.53.5", "1234")
    check_wave_attack_with_same_ip(
        get_random_path_directory, "2.16.53.6", "1235")
    check_wave_attack_with_same_ip(
        get_random_path_extension, "2.16.53.7", "1236")
    check_wave_attack_with_same_ip(get_random_path_query, "2.16.53.8", "1237")

    check_wave_attack_with_same_ip_sliding_window_and_LRU("2.16.53.9", "1238")
    check_wave_attack_with_bypass_ip("2.16.53.10", "1239")


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
