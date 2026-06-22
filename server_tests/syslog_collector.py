import os
import socketserver


LOG_FILE = os.environ.get("SYSLOG_COLLECTOR_LOG_FILE", "/logs/test_logs_sensitive_data.log")
PORT = int(os.environ.get("SYSLOG_COLLECTOR_PORT", "5514"))


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "ab") as log_file:
            while True:
                data = self.request.recv(4096)
                if not data:
                    break
                log_file.write(data)
                if not data.endswith(b"\n"):
                    log_file.write(b"\n")
                log_file.flush()


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "wb"):
        pass

    with Server(("0.0.0.0", PORT), Handler) as server:
        server.serve_forever()
