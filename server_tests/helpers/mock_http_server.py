import os
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'{"status":"ok"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        return


class IPv6HTTPServer(HTTPServer):
    address_family = socket.AF_INET6


host = os.environ.get("BIND_HOST", "0.0.0.0")
port = int(os.environ.get("PORT", "80"))
server_class = IPv6HTTPServer if ":" in host else HTTPServer
server_class((host, port), Handler).serve_forever()
