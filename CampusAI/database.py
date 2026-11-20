import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

import config


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket TEXT UNIQUE,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            photo TEXT,
            student_name TEXT,
            student_id TEXT,
            assigned_to TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            priority TEXT,
            ai_summary TEXT,
            ai_tags TEXT,
            ai_suggested_category TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            note TEXT,
            by_who TEXT,
            at TEXT
        );
        """)


def row_to_dict(r):
    d = dict(r)
    d["ai_tags"] = json.loads(d["ai_tags"]) if d.get("ai_tags") else []
    return d


def create_complaint(data, photo_name, ai):
    with conn() as c:
        cur = c.execute(
            """INSERT INTO complaints (category, description, location, photo, student_name, student_id,
               assigned_to, status, priority, ai_summary, ai_tags, ai_suggested_category, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data["category"], data["description"], data["location"], photo_name,
             data.get("student_name", ""), data.get("student_id", ""),
             config.ROUTING[data["category"]], "pending", ai["priority"], ai["summary"],
             json.dumps(ai["tags"]), ai["suggested_category"], now(), now()),
        )
        cid = cur.lastrowid
        ticket = f"CAI-{datetime.now().year}-{cid:04d}"
        c.execute("UPDATE complaints SET ticket=? WHERE id=?", (ticket, cid))
        c.execute("INSERT INTO history (complaint_id,status,note,by_who,at) VALUES (?,?,?,?,?)",
                  (cid, "pending", "Complaint submitted", "student", now()))
        return ticket


def get_by_ticket(ticket):
    with conn() as c:
        r = c.execute("SELECT * FROM complaints WHERE ticket=?", (ticket,)).fetchone()
        if not r:
            return None
        d = row_to_dict(r)
        d["history"] = [dict(h) for h in c.execute(
            "SELECT status,note,by_who,at FROM history WHERE complaint_id=? ORDER BY id", (d["id"],))]
        return d


def list_for_staff(role, status=None):
    q = "SELECT * FROM complaints WHERE assigned_to=?"
    args = [role]
    if status:
        q += " AND status=?"
        args.append(status)
    q += """ ORDER BY CASE status WHEN 'pending' THEN 0 WHEN 'in-progress' THEN 1 ELSE 2 END,
             CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, id DESC"""
    with conn() as c:
        return [row_to_dict(r) for r in c.execute(q, args)]


def list_for_student(student_id):
    with conn() as c:
        return [row_to_dict(r) for r in c.execute(
            "SELECT * FROM complaints WHERE student_id=? ORDER BY id DESC", (student_id,))]


def update_status(cid, role, status, note):
    with conn() as c:
        r = c.execute("SELECT id FROM complaints WHERE id=? AND assigned_to=?", (cid, role)).fetchone()
        if not r:
            return False
        c.execute("UPDATE complaints SET status=?, updated_at=? WHERE id=?", (status, now(), cid))
        c.execute("INSERT INTO history (complaint_id,status,note,by_who,at) VALUES (?,?,?,?,?)",
                  (cid, status, note or "", role, now()))
        return True


def stats_for_staff(role):
    with conn() as c:
        rows = c.execute("SELECT status, COUNT(*) n FROM complaints WHERE assigned_to=? GROUP BY status",
                         (role,)).fetchall()
    out = {s: 0 for s in config.STATUSES}
    for r in rows:
        out[r["status"]] = r["n"]
    out["total"] = sum(out.values())
    return out
