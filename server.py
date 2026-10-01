"""Serve the local workshop app using Python's standard library only."""

from __future__ import annotations

import json
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

APP_ID = "campus-tasks-python"
ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "app"
HOST = "127.0.0.1"
FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}


def configured_port() -> int:
    try:
        port = int(os.environ.get("CAMPUS_PORT", "4173"))
    except ValueError as error:
        raise ValueError("CAMPUS_PORT must be an integer from 1 to 65535.") from error
    if not 1 <= port <= 65535:
        raise ValueError("CAMPUS_PORT must be an integer from 1 to 65535.")
    return port


class CampusHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        route = urlsplit(self.path).path
        if route == "/health":
            self._send(200, json.dumps({"appId": APP_ID, "sourceRoot": str(ROOT)}).encode(), "application/json")
        elif route == "/api/study-tip":
            self._send(200, json.dumps({"tip": "Break large tasks into smaller steps."}).encode(), "application/json")
        elif route == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
        elif route in FILES:
            filename, content_type = FILES[route]
            try:
                self._send(200, (APP_DIR / filename).read_bytes(), content_type)
            except OSError:
                self._send(500, b"Unable to load app", "text/plain")
        else:
            self._send(404, b"Not found", "text/plain")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        # Keep the test output focused on assertions, not HTTP access logs.
        pass


class CampusHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = False

    def server_bind(self) -> None:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def make_server(port: int | None = None) -> ThreadingHTTPServer:
    server = CampusHTTPServer((HOST, configured_port() if port is None else port), CampusHandler)
    server.daemon_threads = True
    return server


def main() -> None:
    server = make_server()
    print(f"Campus Tasks is ready at http://{HOST}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCampus Tasks stopped.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
