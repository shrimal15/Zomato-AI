"""Serve the recommendation API. This process does not return HTML."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.config import API_HOST, API_PORT
from phase1.store import Catalog
from backend.api import RecommendationApi


class ApiHandler(BaseHTTPRequestHandler):
    api: RecommendationApi

    def do_GET(self) -> None:
        self._respond()

    def do_POST(self) -> None:
        self._respond()

    def do_OPTIONS(self) -> None:
        self._respond()

    def _respond(self) -> None:
        length = self._content_length()
        raw = self.rfile.read(length).decode("utf-8", errors="replace") if length else ""
        response = self.api.handle(
            self.command,
            self.path,
            raw,
            self.headers.get("Origin"),
        )
        payload = b""
        if response.status != 204:
            payload = json.dumps(response.body, ensure_ascii=False).encode("utf-8")
        self.send_response(response.status)
        for name, value in response.headers.items():
            self.send_header(name, value)
        if payload:
            self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def _content_length(self) -> int:
        raw = self.headers.get("Content-Length", "0")
        try:
            return max(int(raw), 0)
        except ValueError:
            return 0

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(
    catalog: Catalog | None = None,
    host: str = API_HOST,
    port: int = API_PORT,
) -> None:
    ApiHandler.api = RecommendationApi(catalog)
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f"Recommendation API at http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
