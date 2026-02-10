import requests
import time
import sys
from testlib import *
from core_api import CoreApi
import os


'''
1. Sets up a simple config and env AIKIDO_BLOCK=1.
2. Sends an attack request to a route, that will cause sending a detection event.
3. Checks that the detection event was submitted and is valid.
'''


def check_shell_injection(collector, s, c, response_code, expected_json):
    start_events = c.get_events("detected_attack")
    response = s.post("/api/execute", {"userCommand": "whoami"})
    collector.soft_assert_response_code_is(response, response_code)

    c.wait_for_new_events(5, old_events_length=len(
        start_events), filter_type="detected_attack")

    all_events = c.get_events("detected_attack")
    new_events = all_events[len(start_events):]

    # Prerequisite: need at least 1 event to check its contents
    if not collector.soft_assert(len(new_events) >= 1, f"Expected at least 1 new event, got {len(new_events)}"):
        return
    assert_event_contains_subset_file(new_events[0], expected_json)


def check_shell_injection_command_post(collector, s, command):
    response = s.post("/api/execute", {"userCommand": command})
    if " not found" in response.text or " must be a string without null bytes" in response.text:
        return
    collector.soft_assert_response_code_is_not(
        response, 200, f"shell injection POST /api/execute {repr(command)} , response: {repr(response.text)[:100]}")


def check_shell_injection_command_get(collector, s, command):
    response = s.get(f"/api/execute/{command}")
    if " not found" in response.text or " must be a string without null bytes" in response.text or " No such file or directory" in response.text:
        return
    collector.soft_assert_response_code_is_not(
        response, 200, f"shell injection GET /api/execute/{repr(command)} , response: {repr(response.text)[:100]}")


def run_test(s: TestServer, c: CoreApi):
    collector = AssertionCollector()

    check_shell_injection(collector, s, c, 500,
                          "expect_detection_blocked.json")

    c.update_runtime_config_file("change_config_disable_blocking.json")
    check_shell_injection(collector, s, c, 200,
                          "expect_detection_not_blocked.json")

    c.update_runtime_config_file("start_config.json")
    check_shell_injection(collector, s, c, 500,
                          "expect_detection_blocked.json")
    commands = [
        # Basic commands
        "whoami",
        "ls -la",
        "pwd",
        "cat /etc/passwd",
        "id",

        # URL encoding variations
        "who%61mi",
        "%77%68%6f%61%6d%69",
        "ls%20-la",
        "cat%20/etc/passwd",

        # Double URL encoding
        "who%2561mi",
        "%2577%2568%256f%2561%256d%2569",

        # Hex encoding
        "\\x77\\x68\\x6f\\x61\\x6d\\x69",

        # Base64 encoding (echo commands)
        "echo d2hvYW1p | base64 -d | sh",
        "echo 'bHMgLWxh' | base64 -d | bash",

        # Case variations
        "WhoAmI",
        "WHOAMI",
        "WhOaMi",

        # Command substitution
        "`whoami`",
        "$(whoami)",
        "$(`whoami`)",

        # Wildcards and globbing
        "who*",
        "who?mi",
        "/bin/wh??mi",
        "/???/whoami",

        # Alternative separators
        "whoami;ls",
        "whoami|ls",
        "whoami&ls",
        "whoami&&ls",
        "whoami||ls",
        "whoami\nls",

        # Quotes and escaping
        "who'a'mi",
        "who\"a\"mi",
        "who\\ami",
        "w'h'o'a'm'i",
        "w\"h\"o\"a\"m\"i",

        # Variable expansion
        "${PATH:0:1}bin${PATH:0:1}whoami",
        "$@who$@ami",

        # Brace expansion
        "{who,ami}",
        "who{a,}mi",

        # Concatenation
        "who''ami",
        "who\"\"ami",
        "wh''o''am''i",

        # Tab and newline characters
        "whoami\t",
        "ls\t-la",
        "whoami\n",

        # Comment injection
        "whoami#comment",
        "whoami;#ls",

        # Redirection tricks
        "whoami>/dev/null",
        "whoami<>/dev/null",

        # Process substitution
        "cat <(whoami)",

        # Environment variable
        "WHO=whoami;$WHO",

        # Backtick variations
        "`` whoami ``",

        # Unicode normalization
        "ⓦⓗⓞⓐⓜⓘ",  # circled letters

        # Nullbyte injection (string representation)
        "whoami%00",
        "whoami\\x00",

        # Line continuation
        "who\\ami",
        "who\\\nami",

        # Alternative command invocation
        "/bin/sh -c whoami",
        "/bin/bash -c 'whoami'",
        "perl -e 'system(whoami)'",
        "python -c 'import os; os.system(\"whoami\")'",

        # Octal encoding
        "\\167\\150\\157\\141\\155\\151",

        # Mixed encoding
        "who%61mi",
        "w\\x68oami",

        # Space alternatives
        "cat</etc/passwd",
        "cat</etc</passwd",
        "{cat,/etc/passwd}",
        "cat${IFS}/etc/passwd",
        "cat$IFS/etc/passwd",

        # Reverse shell commands (for testing)
        "bash -i >& /dev/tcp/127.0.0.1/4444 0>&1",

        # Time-based detection bypass
        "whoami||sleep 5",
        "whoami;sleep 5",

        # Tee command injection
        "whoami|tee /tmp/out",

        # Here document
        "cat<<EOF\nwhoami\nEOF",

        # Array notation (bash)
        "a=(w h o a m i);${a[@]}",
        "ls<-."
    ]
    commands = []

    # \r \v \f \n \t \b \a \e \0 \x00 \u000B \u0000
    special_characters = [
        "\r",
        "\v",
        "\f",
        "\n",
        "\t",
        "\b",
        "\a",
        "\0",
        "\x00",
        "\u000B",
        "\u0000",
    ]
    for special_character in special_characters:
        commands.append(f"id{special_character}-un")
        commands.append(f"ls{special_character}-la")
        commands.append(f"cat{special_character}/etc/passwd")
        commands.append(
            f"echo{special_character}'bHMgLWxh'{special_character}|{special_character}base64{special_character}-d{special_character}|{special_character}bash")

    for command in commands:
        check_shell_injection_command_post(collector, s, command)
        check_shell_injection_command_get(collector, s, command)

    collector.raise_if_failures()


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
