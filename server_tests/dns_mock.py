import ipaddress
import json
import socket
import struct
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


UPSTREAM_DNS = ("127.0.0.11", 53)
HTTP_PORT = 8053
DNS_PORT = 53
TTL_SECONDS = 1

records = {
    "metadata.google.internal": "169.254.169.254",
    "metadata.goog": "169.254.169.254",
    "evil.example.com": "11.22.33.44",
    "domain1.example.com": "11.22.33.44",
    "domain2.example.com": "11.22.33.44",
    "safe.example.com": "11.22.33.44",
    "another-unknown.example.com": "11.22.33.44",
    "unknown.example.com": "11.22.33.44",
    "xn--bse-sna.example.com": "11.22.33.44",
    "xn--mnchen-3ya.example.com": "11.22.33.44",
    "xn--mnchen-allowed-gsb.example.com": "11.22.33.44",
}
records_lock = threading.Lock()


def normalize_hostname(hostname: str) -> str:
    return hostname.rstrip(".").lower()


def read_qname(packet: bytes, offset: int) -> tuple[str, int]:
    labels = []

    while True:
        length = packet[offset]
        offset += 1
        if length == 0:
            break
        labels.append(packet[offset:offset + length].decode("ascii"))
        offset += length

    return normalize_hostname(".".join(labels)), offset


def answer_packet(packet: bytes, ip: str | None, qtype: int, question_end: int) -> bytes:
    transaction_id = packet[:2]
    question = packet[12:question_end + 4]
    flags = b"\x81\x80"
    qdcount = b"\x00\x01"

    if not ip:
        return transaction_id + flags + qdcount + b"\x00\x00\x00\x00\x00\x00" + question

    parsed_ip = ipaddress.ip_address(ip)
    if parsed_ip.version == 4 and qtype == 1:
        rtype = b"\x00\x01"
        rdata = parsed_ip.packed
    elif parsed_ip.version == 6 and qtype == 28:
        rtype = b"\x00\x1c"
        rdata = parsed_ip.packed
    else:
        return transaction_id + flags + qdcount + b"\x00\x00\x00\x00\x00\x00" + question

    answer = (
        b"\xc0\x0c"
        + rtype
        + b"\x00\x01"
        + struct.pack("!I", TTL_SECONDS)
        + struct.pack("!H", len(rdata))
        + rdata
    )
    return transaction_id + flags + qdcount + b"\x00\x01\x00\x00\x00\x00" + question + answer


def servfail_packet(packet: bytes) -> bytes:
    return packet[:2] + b"\x81\x82" + packet[4:6] + b"\x00\x00\x00\x00\x00\x00" + packet[12:]


def forward_to_upstream(packet: bytes) -> bytes:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as upstream:
        upstream.settimeout(5)
        upstream.sendto(packet, UPSTREAM_DNS)
        response, _ = upstream.recvfrom(4096)
        return response


def handle_dns_query(packet: bytes) -> bytes:
    try:
        qname, question_end = read_qname(packet, 12)
        qtype = struct.unpack("!H", packet[question_end:question_end + 2])[0]

        with records_lock:
            ip = records.get(qname)

        if ip is not None:
            return answer_packet(packet, ip, qtype, question_end)
    except Exception:
        pass

    try:
        return forward_to_upstream(packet)
    except Exception:
        return servfail_packet(packet)


def run_dns_server() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as dns_socket:
        dns_socket.bind(("0.0.0.0", DNS_PORT))
        while True:
            packet, address = dns_socket.recvfrom(4096)
            try:
                response = handle_dns_query(packet)
                dns_socket.sendto(response, address)
            except Exception:
                pass


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

    def do_POST(self):
        if self.path != "/records":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("content-length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        hostname = normalize_hostname(body["hostname"])
        ip = str(ipaddress.ip_address(body["ip"]))

        with records_lock:
            records[hostname] = ip

        self.send_response(204)
        self.end_headers()

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    threading.Thread(target=run_dns_server, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), Handler).serve_forever()
