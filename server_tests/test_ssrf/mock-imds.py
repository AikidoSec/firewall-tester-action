#!/usr/bin/env python3
import sys
import os
import json
import ipaddress
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.environ.get("PORT", "80"))


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def ensure_ip_on_lo(ip: str) -> None:
    # Add /32 for IPv4, /128 for IPv6
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError as e:
        print(f"[!] Invalid IP '{ip}': {e}")
        sys.exit(1)

    prefix = "32" if ip_obj.version == 4 else "128"

    # Try to add; ignore "File exists"
    add = run(["ip", "addr", "add", f"{ip}/{prefix}", "dev", "lo"])
    if add.returncode != 0 and "File exists" not in add.stderr:
        print(
            f"[!] Failed to add {ip} to lo: {add.stderr.strip() or add.stdout.strip()}")
        print("    -> You likely need to run as root or grant CAP_NET_ADMIN.")
        sys.exit(1)

    # Verify it's really there
    show = run(["ip", "-j", "addr", "show", "dev", "lo"])
    if show.returncode != 0:
        print(f"[!] Couldn't verify address on lo: {show.stderr.strip()}")
        sys.exit(1)

    # A light-weight check without parsing JSON
    if ip not in show.stdout:
        print(
            f"[!] {ip} does not appear on 'lo' after adding. Output was:\n{show.stdout}")
        sys.exit(1)


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        data = {
            "Code": "Success"
        }
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


def serve_on(ip: str, port: int):
    try:
        httpd = HTTPServer((ip, port), H)
    except OSError as e:
        print(f"[!] Failed to bind to {ip}:{port} -> {e}")
        if e.errno == 99:  # EADDRNOTAVAIL
            print(
                "    -> The IP is not assigned locally. Make sure 'ip addr add' succeeded and you ran as root.")
        sys.exit(1)
    print(f"[+] Serving on http://{ip}:{port}")
    httpd.serve_forever()


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <IP> [IP ...]")
        print("Example:")
        print(f"  sudo {sys.argv[0]} 169.254.169.254 100.100.100.200")
        sys.exit(1)

    ips = sys.argv[1:]
    for ip in ips:
        ensure_ip_on_lo(ip)

    threads = []
    for ip in ips:
        t = threading.Thread(target=serve_on, args=(ip, PORT), daemon=True)
        t.start()
        threads.append(t)

    # Keep the main thread alive
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
