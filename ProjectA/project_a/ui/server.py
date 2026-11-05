"""project_a/ui/server.py

WHAT:  Zero-dependency Python HTTP server hosting the Project A interactive UI.
WHY:   Provides pair-programming evaluators and interviewers an immediate live interface
       without demanding external servers, Node.js, or complex framework setups.
HOW:   Uses standard library `http.server.ThreadingHTTPServer` to dispatch GET and POST requests
       to `project_a.ui.api_handlers` and serve the dashboard HTML.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

# Ensure project_a root is in path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ui.api_handlers import (
    handle_benchmarks,
    handle_calculate,
    handle_law_diff,
    handle_official_checks,
    handle_parse,
)
from ui.html_template import render_index_html


class TaxEngineRequestHandler(BaseHTTPRequestHandler):
    """Dispatches API endpoints and web presentation assets."""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress noisy access logs during automated testing."""
        return

    def _send_json(self, status: int, data: Any) -> None:
        raw = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def _send_html(self, content: str) -> None:
        raw = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_body_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw.strip() else {}

    def do_GET(self) -> None:
        """Handles page and telemetry fetch requests."""
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send_html(render_index_html())
        elif path == "/api/benchmarks":
            self._send_json(200, handle_benchmarks())
        elif path == "/api/official_checks":
            self._send_json(200, handle_official_checks())
        elif path == "/api/law_diff":
            self._send_json(200, handle_law_diff())
        else:
            self._send_json(404, {"error": f"Path not found: {path}"})

    def do_POST(self) -> None:
        """Handles computational and natural language inference requests."""
        path = self.path.split("?")[0]
        try:
            body = self._read_body_json()
            if path == "/api/calculate":
                self._send_json(200, handle_calculate(body))
            elif path == "/api/parse":
                self._send_json(200, handle_parse(body))
            else:
                self._send_json(404, {"error": f"POST endpoint not found: {path}"})
        except Exception as err:
            self._send_json(500, {"error": str(err)})


def run_server(port: int = 8500, open_browser: bool = True) -> None:
    """Starts the HTTP server and optionally opens the browser."""
    server_address = ("127.0.0.1", port)
    server = ThreadingHTTPServer(server_address, TaxEngineRequestHandler)
    url = f"http://localhost:{port}"
    print(f"\n========================================================")
    print(f"  Project A: Income-Tax Engine Dashboard Online")
    print(f"  Local URL: {url}")
    print(f"  Press Ctrl+C to terminate server.")
    print(f"========================================================\n")

    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Project A dashboard server.")
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Project A Tax Engine Dashboard")
    parser.add_argument("--port", type=int, default=8500, help="Port to bind (default: 8500)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open web browser automatically")
    args = parser.parse_args()
    run_server(port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
