from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        body = b'{"status":"ok"}'
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # Discard request logs so they don't clutter test output
    def log_message(self, *args):
        return

HTTPServer(("0.0.0.0", 80), Handler).serve_forever()
