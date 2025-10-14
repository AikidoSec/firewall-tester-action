from testlib import *
from core_api import CoreApi


'''
1. Sets up a simple config and env AIKIDO_BLOCK=1
2. Test that the firewall blocks path traversal attacks
3. Sends an attack request to check the blocking event is submitted
4. Change the config to disable blocking
5. Test that the firewall does not block path traversal attacks
6. Change the config to enable blocking
7. Test that the firewall blocks path traversal attacks
'''


def check_path_traversal_with_event(response_code, expected_json):
    start_events = c.get_events("detected_attack")
    response = s.get("/api/read?path=../secrets/key.txt")
    assert_response_code_is(response, response_code,
                            f"Path traversal check failed {response.text}")

    c.wait_for_new_events(20, old_events_length=len(
        start_events), filter_type="detected_attack")

    all_events = c.get_events("detected_attack")
    new_events = all_events[len(start_events):]

    # assert_events_length_is(new_events, 1)
    assert_event_contains_subset_file(new_events[0], expected_json)


def check_path_traversal(query_string):
    response = s.get(query_string)
    if "File not found" in response.text:
        return
    assert_response_code_is(
        response, 500, f"Path traversal check failed for {query_string} {response.text}")


def run_test(s: TestServer, c: CoreApi):

    # check_path_traversal_with_event(500, "expect_detection_blocked.json")

    # c.update_runtime_config_file("change_config_disable_blocking.json")
    # check_path_traversal_with_event(200, "expect_detection_not_blocked.json")

    # c.update_runtime_config_file("start_config.json")
    # check_path_traversal_with_event(500, "expect_detection_blocked.json")

    paths = [
        "../secrets/key.txt",
        ".%252E/etc/passwd",
        ".%252E/secrets/key.txt",
        "////etc/passwd",
        "../../../etc/passwd",
        "./../secrets/key.txt",
        "..//secrets/key.txt",
        "../////secrets/key.txt",
        ".././/secrets/key.txt",
        "..%2Fsecrets%2Fkey.txt",
        "..%252Fsecrets%252Fkey.txt",
        "..%2e%2e%2fsecrets%2fkey.txt",
        "..\\secrets\\key.txt",
        "../secrets\\key.txt",
        "..%00/secrets/key.txt",
        "....//secrets/key.txt",
        "/../secrets/key.txt",
        "////../secrets/key.txt",
        "..;/secrets/key.txt",
        "..%3B/secrets/key.txt",
        "..%u2216secrets%u2216key.txt",
        "..//secrets//key.txt",
        "..%c0%afsecrets%c0%afkey.txt",
        "..\\\\secrets\\\\key.txt",
        "/../../../../etc/shadow",
        "..//..//..//etc/passwd",
        "..\\\\..\\\\..\\\\windows\\\\win.ini",
        "/ｅｔｃ/ｐａｓｓｗｄ",  # Unicode homoglyphs (lookalike characters)
        "..%252F..%252F..%252Fetc%252Fpasswd",  # URL-encoded with %252F
        "clean_path.txt",
        "file:///files/test/{..}/{..}/etc/passwd",
        "file://localhost/etc/passwd",
        "/.%2e/.%2e/.%2e/.%2e/.%2e/.%2e/etc/passwd",
        "/%%32%65%%32%65/%%32%65%%32%65/%%32%65%%32%65/%%32%65%%32%65/%%32%65%%32%65/%%32%65%%32%65/%%32%65%%32%65/etc/passwd"
        "%2e%2e/%2e%2e/%2e%2e/%2e%2e/%2e%2e/%2e%2e/%2e%2e/etc/passwd"
    ]

    for path in paths:
        variants = [
            # normal
            f"path={path}",

            # duplicate parameters, both with `../secrets/key.txt`
            f"path={path}&path=../secrets/key.txt",
            f"path=../secrets/key.txt&path={path}",

            # empty / missing
            f"path={path}&path=",
            f"path=&path={path}",
            f"path={path}&path",

            # array notation
            f"path[]={path}",
            f"path[0]={path}&path[1]=../secrets/key.txt",
            f"path[]=../secrets/key.txt&path[]={path}",

            # dotted / nested
            f"path={path}&path.foo=../secrets/key.txt",
            f"path={path}&path[foo]=../secrets/key.txt",

            # case variants
            f"path={path}&Path=../secrets/key.txt",
            f"path={path}&PATH=../secrets/key.txt",
            f"Path=../secrets/key.txt&path={path}",

            # separator abuse
            f"path={path};path=../secrets/key.txt",
            f"path={path},path=../secrets/key.txt",

            # fragment trick
            f"path={path}#../secrets/key.txt",

            # encoded second value
            f"path={path}&path=%2E%2E%2Fsecrets%2Fkey.txt",
            # encoded first value
            f"path=%2E%2E%2Fsecrets%2Fkey.txt&path={path}",

        ]

        for variant in variants:
            check_path_traversal("/api/read?" + variant)
            check_path_traversal("/api/read2?" + variant)


if __name__ == "__main__":
    args, s, c = init_server_and_core()
    run_test(s, c)
