#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  PROSPER MOMENTUM — Research Server
═══════════════════════════════════════════════════════════════
  A tiny local web server that lets you type a ticker in your
  browser and instantly get a research page.

  Usage:
    python3 research_server.py          # Starts on port 8765
    python3 research_server.py 9000     # Starts on custom port

  Then open: http://localhost:8765
═══════════════════════════════════════════════════════════════
"""

import json
import os
import sys
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Fix SSL certs before importing yfinance
_MACOS_CERTS = "/etc/ssl/cert.pem"
if os.path.exists(_MACOS_CERTS):
    os.environ.setdefault("SSL_CERT_FILE", _MACOS_CERTS)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _MACOS_CERTS)
    os.environ.setdefault("CURL_CA_BUNDLE", _MACOS_CERTS)

# Import research module
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from research import fetch_company_data, generate_html, generate_private_html, update_index, is_valid_ticker, RESEARCH_DIR

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765


class ResearchHandler(SimpleHTTPRequestHandler):
    """Serves files and handles research API requests."""

    def __init__(self, *args, **kwargs):
        # Serve files from the project directory
        super().__init__(*args, directory=str(SCRIPT_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)

        # API endpoint: /api/research?ticker=NVDA
        if parsed.path == "/api/research":
            params = parse_qs(parsed.query)
            ticker = params.get("ticker", [""])[0].strip()
            if not ticker:
                self._json_response({"error": "No ticker provided"}, 400)
                return
            self._handle_research(ticker)
            return

        # API endpoint: /api/research/list
        if parsed.path == "/api/research/list":
            self._handle_list()
            return

        # Serve the research app at root
        if parsed.path == "/" or parsed.path == "":
            self.path = "/research_app.html"

        # Default: serve static files
        super().do_GET()

    def _handle_research(self, identifier):
        """Fetch data for a company and return JSON."""
        ticker = identifier.upper().replace(" ", "")
        self.log_message(f"Researching: {ticker}")

        try:
            if is_valid_ticker(ticker):
                data = fetch_company_data(ticker)
                if data is None:
                    self._json_response({"error": f"Could not fetch data for {ticker}"}, 500)
                    return

                # Generate and save the HTML page
                html = generate_html(data)
                output_file = RESEARCH_DIR / f"{ticker}.html"
                with open(output_file, "w") as f:
                    f.write(html)
                update_index(ticker, data.get("name", ticker), "public", data.get("sector", ""))

                self._json_response({
                    "status": "ok",
                    "type": "public",
                    "ticker": ticker,
                    "name": data.get("name", ticker),
                    "file": f"research/{ticker}.html",
                    "data": {
                        "price": data.get("price"),
                        "marketCap": data.get("marketCap"),
                        "sector": data.get("sector"),
                        "industry": data.get("industry"),
                        "trailingPE": data.get("trailingPE"),
                        "forwardPE": data.get("forwardPE"),
                        "trailingEps": data.get("trailingEps"),
                        "revenueGrowth": data.get("revenueGrowth"),
                        "grossMargins": data.get("grossMargins"),
                        "targetMean": data.get("targetMean"),
                        "analystCount": data.get("analystCount"),
                        "fiftyTwoWeekHigh": data.get("fiftyTwoWeekHigh"),
                        "fiftyTwoWeekLow": data.get("fiftyTwoWeekLow"),
                        "description": (data.get("description", "") or "")[:500],
                    }
                })
            else:
                # Private company
                safe_id = "".join(c if c.isalnum() else "_" for c in identifier)
                html = generate_private_html(identifier)
                output_file = RESEARCH_DIR / f"_private_{safe_id}.html"
                with open(output_file, "w") as f:
                    f.write(html)
                update_index(safe_id, identifier, "private")

                self._json_response({
                    "status": "ok",
                    "type": "private",
                    "ticker": safe_id,
                    "name": identifier,
                    "file": f"research/_private_{safe_id}.html",
                })
        except Exception as e:
            self._json_response({"error": str(e)}, 500)

    def _handle_list(self):
        """Return list of researched companies."""
        index_file = RESEARCH_DIR / "research_index.json"
        if index_file.exists():
            with open(index_file) as f:
                data = json.load(f)
            self._json_response(data)
        else:
            self._json_response({"companies": []})

    def _json_response(self, data, status=200):
        """Send a JSON response."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """Quieter logging."""
        if "/api/" in (args[0] if args else ""):
            super().log_message(format, *args)


def main():
    server = HTTPServer(("127.0.0.1", PORT), ResearchHandler)
    print(f"""
{'='*60}
  PROSPER MOMENTUM — Research Server
{'='*60}

  Server running at: http://localhost:{PORT}

  Open that URL in your browser to start researching companies.
  Type any ticker (NVDA, AAPL, TSLA...) and hit Enter.

  Press Ctrl+C to stop the server.
{'='*60}
""")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
