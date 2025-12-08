#!/bin/sh
set -e

# Install iproute2 to add the IP alias
apk add --no-cache iproute2 >/dev/null

MOCK_IP="11.22.33.44"
MOCK_PORT="80"

# Assign the fake public IP to loopback in THIS network namespace
ip addr add "${MOCK_IP}/32" dev lo || true

# Create a tiny Python HTTP server that always returns 200 + JSON
cat << 'EOF' > /mock.py
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        body = b'{"status":"ok"}'
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # Prevent noisy logs
    def log_message(self, *args):
        return

HTTPServer(("11.22.33.44", 80), Handler).serve_forever()
EOF

# Run server
python3 /mock.py
