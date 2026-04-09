#!/usr/bin/env python3
"""
Flight Test Resource Planner — local data server
-------------------------------------------------
Serves index.html and handles read/write of data.json so that
multiple people on a shared drive can work from the same dataset.

Usage
-----
  python server.py            # listens on port 8765
  python server.py 9000       # custom port

Then open  http://localhost:8765  (or share your machine's IP
with teammates so they can connect over the network).

Files
-----
  index.html   — the app  (served at /)
  data.json    — the shared dataset  (auto-created on first save)
  server.py    — this file
"""

import json
import os
import sys
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

# ── Config ────────────────────────────────────────────────────
PORT      = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data.json')
_lock     = threading.Lock()          # serialise concurrent writes


# ── Request handler ───────────────────────────────────────────
class Handler(SimpleHTTPRequestHandler):

    def do_GET(self):
        if self.path.split('?')[0] == '/api/data':
            self._serve_data()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/data':
            self._save_data()
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    # ── /api/data  GET ─────────────────────────────────────────
    def _serve_data(self):
        with _lock:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    body = f.read().encode('utf-8')
            else:
                body = b'{}'
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    # ── /api/data  POST ────────────────────────────────────────
    def _save_data(self):
        length = int(self.headers.get('Content-Length', 0))
        raw    = self.rfile.read(length)
        try:
            data = json.loads(raw)               # validate JSON
        except json.JSONDecodeError as e:
            self.send_error(400, 'Invalid JSON: ' + str(e))
            return
        with _lock:
            tmp = DATA_FILE + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, DATA_FILE)           # atomic on most OSes
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, fmt, *args):
        # Suppress noisy static-file logs; show only API calls
        if '/api/' in (args[0] if args else ''):
            print(f'  [{self.address_string()}] {fmt % args}')


# ── Entry point ───────────────────────────────────────────────
if __name__ == '__main__':
    os.chdir(BASE_DIR)
    server = HTTPServer(('0.0.0.0', PORT), Handler)

    import socket
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = '127.0.0.1'

    print()
    print('  Flight Test Resource Planner')
    print('  ════════════════════════════')
    print(f'  Local:    http://localhost:{PORT}')
    print(f'  Network:  http://{local_ip}:{PORT}')
    print(f'  Data:     {DATA_FILE}')
    print()
    print('  Share the Network URL with teammates on the same network.')
    print('  Press Ctrl+C to stop.')
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n  Server stopped.')
