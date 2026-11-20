"""CampusAI server. Pure Python standard library - no pip install needed.

Run:  python server.py   then open http://127.0.0.1:8000
"""

import base64
import json
import mimetypes
import os
import re
import secrets
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import ai_analyzer
import config
import database

SESSIONS = {}  # token -> staff role


class Handler(BaseHTTPRequestHandler):
    server_version = "CampusAI/1.0"

    # ---------- helpers ----------
    def _send(self, code, payload, ctype="application/json"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self):
        n = int(self.headers.get("Content-Length", 0))
        if n > config.MAX_PHOTO_BYTES * 2:
            raise ValueError("Request too large")
        return json.loads(self.rfile.read(n) or b"{}")

    def _staff(self):
        token = self.headers.get("Authorization", "").replace("Bearer ", "")
        return SESSIONS.get(token)

    def _file(self, base, rel):
        path = os.path.normpath(os.path.join(base, rel))
        if not path.startswith(base) or not os.path.isfile(path):
            return self._send(404, {"error": "Not found"})
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            self._send(200, f.read(), ctype)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

    # ---------- GET ----------
    def do_GET(self):
        u = urlparse(self.path)
        p, qs = u.path, parse_qs(u.query)

        if p == "/":
            return self._file(config.STATIC_DIR, "index.html")
        if p == "/staff":
            return self._file(config.STATIC_DIR, "staff.html")
        if p.startswith("/static/"):
            return self._file(config.STATIC_DIR, p[len("/static/"):])
        if p.startswith("/uploads/"):
            return self._file(config.UPLOAD_DIR, p[len("/uploads/"):])

        if p == "/api/my-complaints":
            sid = (qs.get("student_id") or [""])[0].strip()
            if not sid:
                return self._send(400, {"error": "student_id required"})
            return self._send(200, database.list_for_student(sid))

        m = re.fullmatch(r"/api/track/([\w-]+)", p)
        if m:
            c = database.get_by_ticket(m.group(1))
            return self._send(200, c) if c else self._send(404, {"error": "Ticket not found"})

        if p.startswith("/api/staff/"):
            role = self._staff()
            if not role:
                return self._send(401, {"error": "Login required"})
            if p == "/api/staff/complaints":
                status = (qs.get("status") or [None])[0]
                return self._send(200, database.list_for_staff(role, status))
            if p == "/api/staff/stats":
                return self._send(200, database.stats_for_staff(role))
        self._send(404, {"error": "Not found"})

    # ---------- POST / PATCH ----------
    def do_POST(self):
        p = urlparse(self.path).path
        try:
            data = self._json()
        except Exception as e:
            return self._send(400, {"error": str(e)})

        if p == "/api/complaints":
            return self._create(data)

        if p == "/api/staff/login":
            s = config.STAFF.get(data.get("role"))
            if not s or s["pin"] != str(data.get("pin", "")):
                return self._send(401, {"error": "Wrong role or PIN"})
            token = secrets.token_hex(16)
            SESSIONS[token] = data["role"]
            return self._send(200, {"token": token, "name": s["name"], "category": s["category"]})
        self._send(404, {"error": "Not found"})

    def do_PATCH(self):
        p = urlparse(self.path).path
        m = re.fullmatch(r"/api/staff/complaints/(\d+)", p)
        role = self._staff()
        if not m:
            return self._send(404, {"error": "Not found"})
        if not role:
            return self._send(401, {"error": "Login required"})
        try:
            data = self._json()
        except Exception as e:
            return self._send(400, {"error": str(e)})
        if data.get("status") not in config.STATUSES:
            return self._send(400, {"error": "Invalid status"})
        ok = database.update_status(int(m.group(1)), role, data["status"], data.get("note", ""))
        self._send(200, {"ok": True}) if ok else self._send(404, {"error": "Complaint not found for you"})

    def _create(self, d):
        category = d.get("category")
        description = (d.get("description") or "").strip()
        location = (d.get("location") or "").strip()
        if category not in config.CATEGORIES:
            return self._send(400, {"error": "Choose a valid category"})
        if len(description) < 10:
            return self._send(400, {"error": "Description must be at least 10 characters"})
        if not location:
            return self._send(400, {"error": "Location is required"})

        photo_name = None
        photo = d.get("photo")
        if photo:
            m = re.fullmatch(r"data:image/(png|jpeg|jpg|webp);base64,(.+)", photo, re.S)
            if not m:
                return self._send(400, {"error": "Photo must be PNG, JPG or WEBP"})
            raw = base64.b64decode(m.group(2))
            if len(raw) > config.MAX_PHOTO_BYTES:
                return self._send(400, {"error": "Photo too large (max 5 MB)"})
            photo_name = f"{uuid.uuid4().hex}.{'jpg' if m.group(1) == 'jpeg' else m.group(1)}"
            os.makedirs(config.UPLOAD_DIR, exist_ok=True)
            with open(os.path.join(config.UPLOAD_DIR, photo_name), "wb") as f:
                f.write(raw)

        ai = ai_analyzer.analyze(category, description, location)
        ticket = database.create_complaint(
            {"category": category, "description": description, "location": location,
             "student_name": (d.get("student_name") or "")[:80],
             "student_id": (d.get("student_id") or "")[:40]},
            photo_name, ai)
        self._send(201, {"ticket": ticket, "assigned_to": config.STAFF[config.ROUTING[category]]["name"],
                         "priority": ai["priority"], "summary": ai["summary"]})


def main():
    database.init_db()
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    srv = ThreadingHTTPServer((config.HOST, config.PORT), Handler)
    mode = "Claude AI" if config.ANTHROPIC_API_KEY else "built-in rule-based AI"
    print(f"CampusAI running at http://{config.HOST}:{config.PORT}  (analysis: {mode})")
    print(f"Staff dashboard: http://{config.HOST}:{config.PORT}/staff")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
