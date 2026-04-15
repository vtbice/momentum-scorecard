#!/usr/bin/env python3
"""
admin.py — Local admin server for the City of the Future site.

Run:
    python3 scripts/admin.py

This starts a local web server on http://localhost:8765/ that serves the same
fund and watchlist pages as the published static site, but with an "Edit Mode"
toggle that lets you add/remove tickers directly from any card. Changes are
written back to the CSVs and the site is rebuilt automatically.

The published static site (site/) does not contain any admin controls —
admin.js is only served by this local server and is detected at runtime by
checking window.location.hostname.

Ctrl+C to stop the server when you're done editing.
"""
import csv
import json
import os
import subprocess
import sys
import threading
import urllib.parse
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn

PORT = 8765
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = ROOT / "site"
TICKERS_CSV = ROOT.parent / "tickers.csv"
STUDY_JSON = DATA / "study.json"
BUILD_SCRIPT = ROOT / "scripts" / "build_site.py"

FUNDS = [
    "focused-large-cap",
    "large-cap",
    "mid-cap",
    "small-cap",
    "micro-cap",
]

# A lock so concurrent POSTs don't trample each other on CSV writes / rebuilds
write_lock = threading.Lock()


# ========== CSV HELPERS ==========
def read_fund(fund: str) -> list:
    path = DATA / "holdings" / f"{fund}.csv"
    if not path.exists():
        return []
    with path.open() as f:
        return [r["ticker"].strip() for r in csv.DictReader(f) if r["ticker"].strip()]


def write_fund(fund: str, tickers: list):
    """Write tickers to a fund CSV, preserving the header row. Uses LF line endings."""
    path = DATA / "holdings" / f"{fund}.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["ticker"])
        for t in tickers:
            w.writerow([t])


def read_watchlist() -> list:
    if not TICKERS_CSV.exists():
        return []
    with TICKERS_CSV.open() as f:
        return [r["Symbol"].strip() for r in csv.DictReader(f) if r["Symbol"].strip()]


def write_watchlist(tickers: list):
    with TICKERS_CSV.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Symbol"])
        for t in tickers:
            w.writerow([t])


# ========== ACTIONS ==========
def add_to_fund(ticker: str, fund: str) -> dict:
    if fund not in FUNDS:
        return {"ok": False, "error": f"Unknown fund: {fund}"}
    tickers = read_fund(fund)
    if ticker in tickers:
        return {"ok": False, "error": f"{ticker} is already in {fund}"}
    tickers.append(ticker)
    tickers.sort()  # Keep CSVs alphabetized for clean diffs
    write_fund(fund, tickers)
    # Also add to watchlist if not already there
    wl = read_watchlist()
    added_to_wl = False
    if ticker not in wl:
        wl.append(ticker)
        wl.sort()
        write_watchlist(wl)
        added_to_wl = True
    # Clear any former_holding flag
    clear_former_holding(ticker)
    return {
        "ok": True,
        "message": f"Added {ticker} to {fund}" + (" (and to watchlist)" if added_to_wl else ""),
    }


def remove_from_fund(ticker: str, fund: str) -> dict:
    if fund not in FUNDS:
        return {"ok": False, "error": f"Unknown fund: {fund}"}
    tickers = read_fund(fund)
    if ticker not in tickers:
        return {"ok": False, "error": f"{ticker} is not in {fund}"}
    tickers.remove(ticker)
    write_fund(fund, tickers)

    # If removed from every fund, flag as former holding
    still_held = any(ticker in read_fund(f) for f in FUNDS)
    if not still_held:
        mark_former_holding(ticker)
        return {
            "ok": True,
            "message": f"Removed {ticker} from {fund}. Now watchlist-only (tagged as former holding).",
            "demoted": True,
        }
    return {"ok": True, "message": f"Removed {ticker} from {fund}"}


def demote(ticker: str) -> dict:
    """Remove ticker from every fund; keep on watchlist; tag as former holding."""
    removed_from = []
    for fund in FUNDS:
        tickers = read_fund(fund)
        if ticker in tickers:
            tickers.remove(ticker)
            write_fund(fund, tickers)
            removed_from.append(fund)
    if not removed_from:
        return {"ok": False, "error": f"{ticker} was not in any fund"}
    mark_former_holding(ticker)
    return {
        "ok": True,
        "message": f"Demoted {ticker} (removed from {', '.join(removed_from)}). Still on watchlist.",
    }


def add_to_watchlist(ticker: str) -> dict:
    wl = read_watchlist()
    if ticker in wl:
        return {"ok": False, "error": f"{ticker} is already on the watchlist"}
    wl.append(ticker)
    wl.sort()
    write_watchlist(wl)
    return {"ok": True, "message": f"Added {ticker} to watchlist"}


def remove_from_watchlist(ticker: str) -> dict:
    wl = read_watchlist()
    if ticker not in wl:
        return {"ok": False, "error": f"{ticker} is not on the watchlist"}
    # Safety: don't let users remove a ticker that's still held in a fund
    for fund in FUNDS:
        if ticker in read_fund(fund):
            return {
                "ok": False,
                "error": f"{ticker} is still held in {fund}. Remove it from the fund first.",
            }
    wl.remove(ticker)
    write_watchlist(wl)
    return {"ok": True, "message": f"Removed {ticker} from watchlist"}


def mark_former_holding(ticker: str):
    """Tag a ticker in study.json as a former holding with today's date."""
    if not STUDY_JSON.exists():
        return
    with STUDY_JSON.open() as f:
        study = json.load(f)
    if ticker in study.get("companies", {}):
        study["companies"][ticker]["status"] = "former_holding"
        study["companies"][ticker]["last_held"] = str(date.today())
        with STUDY_JSON.open("w") as f:
            json.dump(study, f, indent=2, ensure_ascii=False)


def clear_former_holding(ticker: str):
    """Remove the former_holding flag when a ticker is re-added to any fund."""
    if not STUDY_JSON.exists():
        return
    with STUDY_JSON.open() as f:
        study = json.load(f)
    entry = study.get("companies", {}).get(ticker)
    if entry and entry.get("status") == "former_holding":
        entry.pop("status", None)
        entry.pop("last_held", None)
        with STUDY_JSON.open("w") as f:
            json.dump(study, f, indent=2, ensure_ascii=False)


# ========== REBUILD ==========
def rebuild_site() -> dict:
    """Run build_site.py to regenerate all HTML."""
    try:
        result = subprocess.run(
            [sys.executable, str(BUILD_SCRIPT)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return {"ok": True, "message": "Site rebuilt"}
        else:
            return {"ok": False, "error": f"Build failed: {result.stderr[:500]}"}
    except Exception as e:
        return {"ok": False, "error": f"Rebuild error: {e}"}


# ========== ADMIN CLIENT JS ==========
# This is the admin.js file served to the browser when in admin mode.
# It adds edit-mode controls on top of the existing pages.
ADMIN_JS = r"""
// admin.js — only loaded when running from the local admin server.
// Adds an Edit Mode toggle and in-page add/remove controls.
(function() {
  const FUNDS_BY_SLUG = {
    'focused-large-cap': 'Focused Large Cap',
    'large-cap': 'Large Cap',
    'mid-cap': 'Mid Cap',
    'small-cap': 'Small Cap',
    'micro-cap': 'Micro Cap',
  };

  // Mark the body so the read-only banner is hidden
  document.body.classList.add('admin-mode');

  // Detect current page from URL
  const path = window.location.pathname.replace(/^\//, '').replace(/\.html$/, '') || 'index';
  const currentFund = Object.keys(FUNDS_BY_SLUG).indexOf(path) !== -1 ? path : null;
  const isOverview = path === 'index';
  const isWatchlist = path === 'watchlist';

  // Inject admin CSS
  const style = document.createElement('style');
  style.textContent = `
    .admin-bar {
      position: fixed;
      top: 0; left: 0; right: 0;
      background: #10b981;
      color: white;
      padding: 10px 24px;
      font-family: 'DM Sans', sans-serif;
      font-size: 13px;
      font-weight: 600;
      z-index: 999;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
    }
    .admin-bar.hidden { display: none; }
    .admin-bar-label { letter-spacing: 0.06em; text-transform: uppercase; }
    .admin-bar-controls { display: flex; gap: 10px; align-items: center; }
    .admin-bar input {
      padding: 5px 10px;
      border: none;
      border-radius: 4px;
      background: rgba(255, 255, 255, 0.25);
      color: white;
      font-family: inherit;
      font-size: 12px;
      width: 140px;
    }
    .admin-bar input::placeholder { color: rgba(255, 255, 255, 0.7); }
    .admin-bar button, .admin-bar select {
      padding: 5px 12px;
      border: 1px solid rgba(255, 255, 255, 0.4);
      background: rgba(255, 255, 255, 0.15);
      color: white;
      font-family: inherit;
      font-size: 12px;
      font-weight: 600;
      border-radius: 4px;
      cursor: pointer;
      letter-spacing: 0.04em;
    }
    .admin-bar button:hover, .admin-bar select:hover { background: rgba(255, 255, 255, 0.3); }
    body.admin-active { padding-top: 44px; }

    .edit-mode-strip {
      background: #10b981;
      color: white;
      padding: 10px 24px;
      text-align: center;
      font-family: 'DM Sans', sans-serif;
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.04em;
      border-bottom: 3px solid #059669;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 14px;
      position: sticky;
      top: 0;
      z-index: 999;
    }
    .edit-mode-strip-label {
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 11px;
      font-weight: 700;
    }
    .admin-toggle {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      background: rgba(255, 255, 255, 0.18);
      color: white;
      border: 1px solid rgba(255, 255, 255, 0.5);
      border-radius: 5px;
      font-family: 'DM Sans', sans-serif;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      transition: all 0.15s;
    }
    .admin-toggle:hover { background: rgba(255, 255, 255, 0.3); }
    .admin-toggle.active {
      background: white;
      color: #059669;
      border-color: white;
    }

    /* These buttons are created by admin.js ONLY when edit mode is on
       and removed from the DOM when edit mode is off. No display:none
       tricks — if it exists, it's visible. */
    .card-delete, .card-demote {
      display: inline-flex !important;
      align-items: center;
      margin-left: auto;
      padding: 5px 12px;
      background: #fee2e2;
      border: 2px solid #dc2626;
      border-radius: 6px;
      color: #991b1b;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      cursor: pointer;
      box-shadow: 0 1px 3px rgba(220, 38, 38, 0.2);
      white-space: nowrap;
    }
    .card-demote {
      background: #fef3c7;
      border-color: #d97706;
      color: #78350f;
      margin-left: 8px;
      box-shadow: 0 1px 3px rgba(217, 119, 6, 0.2);
    }
    .card-delete:hover { background: #dc2626; color: white; }
    .card-demote:hover { background: #d97706; color: white; }
    .wl-delete {
      display: inline-flex !important;
      align-items: center;
      justify-content: center;
      padding: 4px 10px;
      background: #fee2e2;
      border: 2px solid #dc2626;
      border-radius: 5px;
      color: #991b1b;
      font-size: 12px;
      font-weight: 800;
      cursor: pointer;
      margin-left: 4px;
    }
    .wl-delete:hover { background: #dc2626; color: white; }

    .admin-toast {
      position: fixed;
      bottom: 80px;
      right: 24px;
      padding: 12px 20px;
      background: #0f172a;
      color: white;
      border-radius: 8px;
      font-family: 'DM Sans', sans-serif;
      font-size: 13px;
      font-weight: 500;
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
      z-index: 1001;
      max-width: 320px;
      opacity: 0;
      transform: translateY(10px);
      transition: all 0.2s;
    }
    .admin-toast.show { opacity: 1; transform: translateY(0); }
    .admin-toast.success { border-left: 4px solid #10b981; }
    .admin-toast.error { border-left: 4px solid #ef4444; }
  `;
  document.head.appendChild(style);

  // Toast helper
  let toastEl = null;
  function toast(message, kind) {
    if (!toastEl) {
      toastEl = document.createElement('div');
      toastEl.className = 'admin-toast';
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = message;
    toastEl.className = 'admin-toast show ' + (kind || 'success');
    setTimeout(function() { toastEl.classList.remove('show'); }, 3500);
  }

  // API helper
  async function api(path, body) {
    try {
      const res = await fetch(path, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)
      });
      const data = await res.json();
      return data;
    } catch (e) {
      return {ok: false, error: String(e)};
    }
  }

  async function afterChange(result) {
    if (result.ok) {
      toast(result.message || 'Saved', 'success');
      // Rebuild, then soft-reload
      const rb = await api('/api/rebuild', {});
      if (rb.ok) {
        setTimeout(function() { window.location.reload(); }, 600);
      } else {
        toast('Rebuild failed: ' + rb.error, 'error');
      }
    } else {
      toast(result.error || 'Failed', 'error');
    }
  }

  // ========== EDIT MODE STRIP ==========
  // Full-width green strip at the very top — impossible to miss.
  const strip = document.createElement('div');
  strip.className = 'edit-mode-strip';
  strip.innerHTML =
    '<span class="edit-mode-strip-label">✎ Edit Mode Active</span>' +
    '<span style="opacity:0.85;">Click the button to show in-page add/remove controls</span>';

  const toggle = document.createElement('button');
  toggle.className = 'admin-toggle';
  toggle.textContent = '✎ Show Edit Controls';
  strip.appendChild(toggle);

  document.body.prepend(strip);

  // IMPORTANT: declare `adminBar` BEFORE any call to applyEditMode() —
  // otherwise hideAdminBar()/showAdminBar() hit a temporal-dead-zone
  // ReferenceError for the `let`-scoped `adminBar`, the IIFE throws,
  // and the toggle click listener never attaches.
  let adminBar = null;
  let editMode = localStorage.getItem('cityEditMode') === '1';

  toggle.addEventListener('click', function() {
    editMode = !editMode;
    localStorage.setItem('cityEditMode', editMode ? '1' : '0');
    applyEditMode();
  });

  // Apply initial state AFTER the listener is attached and adminBar is initialized
  applyEditMode();

  function applyEditMode() {
    if (editMode) {
      document.body.classList.add('admin-active');
      toggle.classList.add('active');
      toggle.textContent = '✕ Hide Edit Controls';
      showAdminBar();
      injectCardButtons();
    } else {
      document.body.classList.remove('admin-active');
      toggle.classList.remove('active');
      toggle.textContent = '✎ Show Edit Controls';
      hideAdminBar();
      removeCardButtons();
    }
  }

  function removeCardButtons() {
    document.querySelectorAll('.card-delete, .card-demote, .wl-delete').forEach(function(b) {
      b.remove();
    });
  }

  // ========== ADMIN BAR ==========
  function showAdminBar() {
    if (adminBar) { adminBar.classList.remove('hidden'); return; }
    adminBar = document.createElement('div');
    adminBar.className = 'admin-bar';

    if (currentFund) {
      adminBar.innerHTML =
        '<span class="admin-bar-label">Edit Mode · ' + FUNDS_BY_SLUG[currentFund] + '</span>' +
        '<div class="admin-bar-controls">' +
          '<input type="text" id="admin-add-input" placeholder="Ticker to add" maxlength="8" />' +
          '<button id="admin-add-btn">Add to ' + FUNDS_BY_SLUG[currentFund] + '</button>' +
        '</div>';
    } else if (isOverview) {
      const fundOpts = Object.keys(FUNDS_BY_SLUG).map(function(s) {
        return '<option value="' + s + '">' + FUNDS_BY_SLUG[s] + '</option>';
      }).join('');
      adminBar.innerHTML =
        '<span class="admin-bar-label">Edit Mode · Overview (all funds)</span>' +
        '<div class="admin-bar-controls">' +
          '<input type="text" id="admin-add-input" placeholder="Ticker" maxlength="8" />' +
          '<select id="admin-fund-select">' + fundOpts + '</select>' +
          '<button id="admin-add-btn">Add</button>' +
        '</div>';
    } else if (isWatchlist) {
      adminBar.innerHTML =
        '<span class="admin-bar-label">Edit Mode · Watchlist</span>' +
        '<div class="admin-bar-controls">' +
          '<input type="text" id="admin-add-input" placeholder="Ticker to watch" maxlength="8" />' +
          '<button id="admin-add-btn">Add to Watchlist</button>' +
        '</div>';
    }
    document.body.prepend(adminBar);

    const addBtn = document.getElementById('admin-add-btn');
    const addInput = document.getElementById('admin-add-input');
    const fundSelect = document.getElementById('admin-fund-select');
    if (addBtn && addInput) {
      async function doAdd() {
        const ticker = addInput.value.trim().toUpperCase();
        if (!ticker) return;
        let result;
        if (currentFund) {
          result = await api('/api/fund/add', {ticker: ticker, fund: currentFund});
        } else if (isOverview && fundSelect) {
          result = await api('/api/fund/add', {ticker: ticker, fund: fundSelect.value});
        } else if (isWatchlist) {
          result = await api('/api/watchlist/add', {ticker: ticker});
        }
        if (result) await afterChange(result);
      }
      addBtn.addEventListener('click', doAdd);
      addInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') doAdd();
      });
    }

    // Inject per-card delete/demote buttons
    injectCardButtons();
  }

  function hideAdminBar() {
    if (adminBar) adminBar.classList.add('hidden');
  }

  // ========== PER-CARD CONTROLS ==========
  function injectCardButtons() {
    const cards = document.querySelectorAll('.card');
    const rows = document.querySelectorAll('.wl-row');
    console.log('[admin.js] injectCardButtons: path=' + path + ', currentFund=' + currentFund + ', isOverview=' + isOverview + ', isWatchlist=' + isWatchlist + ', cards=' + cards.length + ', rows=' + rows.length);
    if (currentFund) {
      // Fund page: add "Remove from fund" button to each card
      cards.forEach(function(card) {
        const ticker = card.id;
        if (!ticker || card.querySelector('.card-delete')) return;
        const btn = document.createElement('button');
        btn.className = 'card-delete';
        btn.textContent = '✕ Remove';
        btn.title = 'Remove from ' + FUNDS_BY_SLUG[currentFund];
        btn.addEventListener('click', async function(e) {
          e.stopPropagation();
          if (!confirm('Remove ' + ticker + ' from ' + FUNDS_BY_SLUG[currentFund] + '?')) return;
          const result = await api('/api/fund/remove', {ticker: ticker, fund: currentFund});
          await afterChange(result);
        });
        const head = card.querySelector('.card-head');
        if (head) head.appendChild(btn);
      });
    } else if (isOverview) {
      // Overview: add "Demote" button to each card (removes from all funds, keeps watchlist)
      cards.forEach(function(card) {
        const ticker = card.id;
        if (!ticker || card.querySelector('.card-demote')) return;
        const btn = document.createElement('button');
        btn.className = 'card-demote';
        btn.textContent = '↓ Demote';
        btn.title = 'Remove from all funds (keeps on watchlist)';
        btn.addEventListener('click', async function(e) {
          e.stopPropagation();
          if (!confirm('Remove ' + ticker + ' from ALL funds? It will stay on the watchlist.')) return;
          const result = await api('/api/fund/demote', {ticker: ticker});
          await afterChange(result);
        });
        const head = card.querySelector('.card-head');
        if (head) head.appendChild(btn);
      });
    } else if (isWatchlist) {
      // Watchlist: add "Remove" button to each row in the actions cell
      rows.forEach(function(row) {
        if (row.querySelector('.wl-delete')) return;
        const tickerLink = row.querySelector('.wl-ticker');
        if (!tickerLink) return;
        const ticker = tickerLink.textContent.trim();
        const actionsCell = row.querySelector('.wl-actions');
        if (!actionsCell) return;
        const btn = document.createElement('button');
        btn.className = 'wl-delete';
        btn.textContent = '✕';
        btn.title = 'Remove ' + ticker + ' from watchlist (will fail if still held)';
        btn.addEventListener('click', async function(e) {
          e.stopPropagation();
          if (!confirm('Remove ' + ticker + ' from the watchlist?')) return;
          const result = await api('/api/watchlist/remove', {ticker: ticker});
          await afterChange(result);
        });
        actionsCell.appendChild(btn);
      });
    }
  }
})();
"""


# ========== HTTP HANDLER ==========
class AdminHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Quiet the default noisy logging; show only POST actions
        if self.command == "POST":
            sys.stderr.write("[admin] %s %s\n" % (self.command, self.path))

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str = None):
        if not path.exists():
            self.send_error(404)
            return
        if content_type is None:
            ext = path.suffix.lower()
            content_type = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css",
                ".js": "application/javascript",
                ".json": "application/json",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".svg": "image/svg+xml",
            }.get(ext, "application/octet-stream")
        data = path.read_bytes()
        # Inject admin.js loader into HTML files
        if content_type.startswith("text/html"):
            injection = b'<script src="/admin.js"></script></body>'
            data = data.replace(b"</body>", injection)
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "":
            self.send_response(302)
            self.send_header("Location", "/index.html")
            self.end_headers()
            return

        if path == "/admin.js":
            body = ADMIN_JS.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return

        # Serve static files from site/
        file_path = SITE / path.lstrip("/")
        if file_path.exists() and file_path.is_file():
            self._send_file(file_path)
            return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw) if raw else {}
        except Exception:
            self._send_json({"ok": False, "error": "Invalid JSON"}, 400)
            return

        with write_lock:
            result = self._dispatch(self.path, body)
        self._send_json(result)

    def _dispatch(self, path: str, body: dict) -> dict:
        ticker = str(body.get("ticker", "")).strip().upper()
        fund = body.get("fund", "")
        if path == "/api/fund/add":
            if not ticker or not fund:
                return {"ok": False, "error": "Missing ticker or fund"}
            return add_to_fund(ticker, fund)
        if path == "/api/fund/remove":
            if not ticker or not fund:
                return {"ok": False, "error": "Missing ticker or fund"}
            return remove_from_fund(ticker, fund)
        if path == "/api/fund/demote":
            if not ticker:
                return {"ok": False, "error": "Missing ticker"}
            return demote(ticker)
        if path == "/api/watchlist/add":
            if not ticker:
                return {"ok": False, "error": "Missing ticker"}
            return add_to_watchlist(ticker)
        if path == "/api/watchlist/remove":
            if not ticker:
                return {"ok": False, "error": "Missing ticker"}
            return remove_from_watchlist(ticker)
        if path == "/api/rebuild":
            return rebuild_site()
        return {"ok": False, "error": f"Unknown endpoint: {path}"}


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main():
    # Ensure site is built before starting
    if not SITE.exists() or not (SITE / "index.html").exists():
        print("[admin] Building site first...")
        rebuild_site()

    server = ThreadingHTTPServer(("127.0.0.1", PORT), AdminHandler)
    url = f"http://localhost:{PORT}/index.html"
    print(f"\n  City of the Future — admin server")
    print(f"  ─────────────────────────────────")
    print(f"  Running at {url}")
    print(f"  Press Ctrl+C to stop\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[admin] Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
