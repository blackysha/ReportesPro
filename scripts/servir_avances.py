"""Servir únicamente el registro de avances en la red local."""

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import IPv4Address
from pathlib import Path
from urllib.parse import urlsplit

PAGE = Path(__file__).resolve().parents[1] / "docs" / "avances.html"


class ProgressHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_page(include_body=True)

    def do_HEAD(self):
        self.send_page(include_body=False)

    def send_page(self, include_body):
        if urlsplit(self.path).path != "/avances":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content = PAGE.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if include_body:
            self.wfile.write(content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direccion", type=IPv4Address, required=True)
    parser.add_argument("--puerto", type=int, default=8504)
    args = parser.parse_args()
    if not (args.direccion.is_private and not args.direccion.is_unspecified):
        parser.error("Indica una dirección IPv4 privada de esta PC.")
    with ThreadingHTTPServer((str(args.direccion), args.puerto), ProgressHandler) as server:
        server.serve_forever()
