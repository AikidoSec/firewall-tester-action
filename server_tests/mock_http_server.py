import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "80"))
READY_FILE = os.environ.get("READY_FILE", "/tmp/mock-http-ready")
RESPONSE_BODY = os.environ.get("RESPONSE_BODY", "{}").encode()
CONTENT_TYPE = os.environ.get("CONTENT_TYPE", "application/json")
ENABLE_IPV6 = os.environ.get("ENABLE_IPV6", "0") == "1"
IPV6_HOST = os.environ.get("IPV6_HOST", "::")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.respond()

    def do_POST(self):
        self.respond()

    def respond(self):
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE)
        self.send_header("Content-Length", str(len(RESPONSE_BODY)))
        self.end_headers()
        self.wfile.write(RESPONSE_BODY)

    def log_message(self, *_):
        return


class ThreadingHTTPServerV6(ThreadingHTTPServer):
    address_family = socket.AF_INET6

    def server_bind(self):
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        super().server_bind()


def create_servers():
    servers = [ThreadingHTTPServer((HOST, PORT), Handler)]

    if ENABLE_IPV6:
        try:
            servers.append(ThreadingHTTPServerV6((IPV6_HOST, PORT), Handler))
        except OSError as e:
            print(f"IPv6 listener disabled: {e}", flush=True)

    return servers


def main():
    servers = create_servers()
    with open(READY_FILE, "w", encoding="utf-8") as ready:
        ready.write("ready\n")

    threads = []
    for server in servers:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()


if __name__ == "__main__":
    main()
