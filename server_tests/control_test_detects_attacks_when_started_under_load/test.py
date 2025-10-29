

from testlib import *
from core_api import CoreApi
import threading
import random
import time

"""
Test that verifies the firewall can detect and block multiple attack types
(path traversal, SQL injection, shell injection, and SSRF) when the server
starts under heavy concurrent traffic.
"""


def send_attacks():
    # path traversal attacks
    for _ in range(2):
        response = s.get("/api/read?path=../secrets/key.txt")
        assert_response_code_is(response, 500,
                                f"Request failed: {response.text} {cs.get_server_logs()}")
        assert_response_body_contains(
            response, "firewall has blocked a path traversal", f"{response.text} {cs.get_server_logs()}")

    # sql injection attacks
    for _ in range(2):
        response = s.post(
            "/api/create", {"name": "Malicious Pet', 'Gru from the Minions') --"})
        assert_response_code_is(response, 500,
                                f"Request failed: {response.text} {cs.get_server_logs()}")
        assert_response_body_contains(
            response, "firewall has blocked an SQL injection", f"{response.text} {cs.get_server_logs()}")

    # shell injection attacks
    for _ in range(2):
        response = s.post("/api/execute", {"userCommand": "whoami"})
        assert_response_code_is(response, 500,
                                f"Request failed: {response.text} {cs.get_server_logs()}")
        assert_response_body_contains(
            response, "firewall has blocked a shell injection", f"{response.text} {cs.get_server_logs()}")

    # ssrf attacks
    for _ in range(2):
        response = s.post(
            "/api/request", {"url": "http://127.0.0.1:8081"}, timeout=10)
        assert_response_code_is(response, 500,
                                f"Request failed: {response.text} {cs.get_server_logs()}")
        assert_response_body_contains(
            response, "firewall has blocked a server-side request forgery", f"{response.text} {cs.get_server_logs()}")


def check_event_is_submitted_shell_injection(response_code, expected_json):
    start_events = c.get_events("detected_attack")
    response = s.post("/api/execute", {"userCommand": "whoami"})
    assert_response_code_is(response, response_code)

    c.wait_for_new_events(5, old_events_length=len(
        start_events), filter_type="detected_attack")

    all_events = c.get_events("detected_attack")
    new_events = all_events[len(start_events):]
    assert_events_length_is(new_events, 1)
    assert_event_contains_subset_file(new_events[0], expected_json)


def traffic_generator(stop_event):
    """Generate diverse traffic with various IPs, user agents, and endpoints"""

    # IP ranges by region
    IP_RANGES = {
        'NA': ['64.', '98.', '208.', '66.'],
        'EU': ['81.', '82.', '85.', '86.', '87.'],
        'AS': ['101.', '103.', '106.', '111.', '112.'],
        'SA': ['177.', '179.', '181.', '186.', '187.'],
        'AF': ['41.', '102.', '105.', '154.', '196.'],
        'OC': ['1.', '27.', '58.', '203.']
    }

    # User agents categorized
    USER_AGENTS = [
        # AI Data Scrapers (30% chance)
        'Mozilla/5.0 (compatible; GPTBot/1.0)',
        'Mozilla/5.0 (compatible; ClaudeBot/1.0)',
        'Mozilla/5.0 (compatible; Bytespider/1.0)',
        'Mozilla/5.0 (compatible; CCBot/2.0)',
        'Mozilla/5.0 (compatible; Google-Extended/1.0)',

        # SEO Crawlers
        'Mozilla/5.0 (compatible; AhrefsBot/7.0)',
        'Mozilla/5.0 (compatible; SemrushBot/7.0)',
        'Mozilla/5.0 (compatible; MJ12bot/v1.4.8)',
        'Mozilla/5.0 (compatible; SEOkicks/0.1)',

        # Search Engines
        'Mozilla/5.0 (compatible; Googlebot/2.1)',
        'Mozilla/5.0 (compatible; bingbot/2.0)',
        'Mozilla/5.0 (compatible; DuckDuckBot/1.0)',
        'Mozilla/5.0 (compatible; Baiduspider/2.0)',
        'Mozilla/5.0 (compatible; YandexBot/3.0)',

        # Vulnerability scanners
        'sqlmap/1.0',
        'Nikto/2.1.6',
        'Mozilla/5.0 (compatible; Nmap Scripting Engine)',
        'WPScan v3.8.0',

        # Normal browsers
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edge/91.0.864.59',
    ]

    # Test endpoints
    ENDPOINTS = [
        {'method': 'get', 'path': '/api/pets/'},
        {'method': 'get', 'path': '/api/pets/1'},
        {'method': 'post', 'path': '/api/pets/',
            'data': {'name': 'Fluffy', 'type': 'cat'}},
        {'method': 'get', 'path': '/'},
        {'method': 'get', 'path': '/health'},
    ]

    # Generate IP pool
    ip_pool = []
    for region, prefixes in IP_RANGES.items():
        for _ in range(20):  # 20 IPs per region
            prefix = random.choice(prefixes)
            ip = f"{prefix}{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
            ip_pool.append(ip)

    # Generate traffic
    for i in range(10000):
        if stop_event.is_set():
            break

        try:
            # Select random IP and user agent
            ip = random.choice(ip_pool)
            user_agent = random.choice(USER_AGENTS)

            # Build headers
            headers = {
                'X-Forwarded-For': ip,
                'X-Real-IP': ip,
                'User-Agent': user_agent,
            }

            # 70% chance it's a normal user (not a bot)
            if 'Mozilla/5.0 (Windows' in user_agent or 'Mozilla/5.0 (Macintosh' in user_agent:
                # Add user ID and name for normal users
                user_id = random.randint(10000, 99999)
                names = ['Alice', 'Bob', 'Charlie', 'David', 'Emma', 'Frank', 'Grace',
                         'Henry', 'Isabella', 'Jack', 'Kate', 'Liam', 'Mia', 'Noah', 'Olivia']
                user_name = names[user_id % len(names)]
                headers['X-User-ID'] = str(user_id)
                headers['X-User-Name'] = user_name

            # Select random endpoint
            endpoint = random.choice(ENDPOINTS)

            # Make request
            if endpoint['method'] == 'get':
                response = s.get(endpoint['path'], headers=headers)
            elif endpoint['method'] == 'post':
                response = s.post(endpoint['path'], endpoint.get(
                    'data', {}), headers=headers)

            # Small delay to avoid overwhelming the server
            if i % 100 == 0:
                time.sleep(0.01)

        except Exception as e:
            # Continue on error
            pass


def run_test(s: TestServer, c: CoreApi, cs: TestControlServer):
    cs.check_health()
    cs.stop_server()
    cs.kill_agent()
    cs.status_is_running(False)

    stop_event = threading.Event()
    thread = threading.Thread(target=traffic_generator, args=(stop_event,))
    thread.start()

    cs.start_server()
    cs.status_is_running(True)
    time.sleep(10)
    send_attacks()
    check_event_is_submitted_shell_injection(
        500, "expect_detection_blocked.json")

    # Stop the traffic generator thread
    stop_event.set()
    thread.join()


if __name__ == "__main__":
    args, s, c, cs = init_server_and_core()
    run_test(s, c, cs)
