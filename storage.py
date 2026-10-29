"""SQLite persistence. Message IDs are monotonic across application restarts."""
import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path


class Store:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "orion.sqlite3"
        self.lock = threading.RLock()
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT NOT NULL, text TEXT NOT NULL, extras TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, kind TEXT, label TEXT, status TEXT, current REAL DEFAULT 0, total REAL DEFAULT 1, result TEXT DEFAULT '{}', created REAL, updated REAL);
                CREATE TABLE IF NOT EXISTS usage(id INTEGER PRIMARY KEY, provider TEXT, model TEXT, input_tokens INTEGER, output_tokens INTEGER, seconds REAL, created REAL);
            """)
            if 'thread_id' not in {r[1] for r in db.execute('PRAGMA table_info(messages)')}:
                db.execute('ALTER TABLE messages ADD COLUMN thread_id TEXT')
            db.execute('CREATE INDEX IF NOT EXISTS messages_thread ON messages(thread_id,id)')
            db.execute('CREATE INDEX IF NOT EXISTS messages_statistics ON messages(sender,created)')
            db.execute('CREATE INDEX IF NOT EXISTS usage_statistics ON usage(created)')
            db.execute("UPDATE jobs SET status='interrupted' WHERE status IN ('queued','running')")
            db.execute("UPDATE jobs SET kind='video' WHERE kind='generate_video'")
            db.execute("UPDATE jobs SET kind='image' WHERE kind='generate_image'")

    def connection(self):
        return sqlite3.connect(self.path, timeout=20)

    def get(self, key, default=None):
        with self.connection() as db:
            row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, key, value):
        with self.lock, self.connection() as db:
            db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(value, ensure_ascii=False)))

    def message(self, sender, text, **extras):
        with self.lock, self.connection() as db:
            cursor = db.execute("INSERT INTO messages(sender,text,extras,created,thread_id) VALUES (?,?,?,?,?)", (sender, str(text), json.dumps(extras, ensure_ascii=False), time.time(), extras.get('thread_id')))
            return cursor.lastrowid

    def messages(self, since=0, limit=500, thread_id=None, global_only=False):
        with self.connection() as db:
            clause, params = (' AND thread_id=?', [thread_id]) if thread_id else (' AND thread_id IS NULL', []) if global_only else ('', [])
            rows = db.execute("SELECT id,sender,text,extras,created FROM messages WHERE id>=?" + clause + " ORDER BY id LIMIT ?", [since, *params, min(500, limit)]).fetchall()
        return [dict(id=r[0], sender=r[1], text=r[2], created=r[4], **json.loads(r[3])) for r in rows]

    def next_message_id(self):
        """Start a clean visible session without removing persistent messages."""
        with self.connection() as db:
            return db.execute("SELECT COALESCE(MAX(id),0)+1 FROM messages").fetchone()[0]

    def history(self, limit=24, before=None):
        cutoff = before if before is not None else 2**62
        with self.connection() as db:
            current = db.execute('SELECT thread_id FROM messages WHERE id=?', (before,)).fetchone() if before is not None else None
            thread = current[0] if current else None
            clause, params = ('thread_id=?', [thread]) if thread else ('thread_id IS NULL', [])
            rows = db.execute("SELECT id,sender,text,extras FROM messages WHERE sender IN ('user','orion') AND " + clause + " ORDER BY id DESC LIMIT 200", params).fetchall()
        items = [dict(id=r[0], sender=r[1], text=r[2], **json.loads(r[3])) for r in rows]
        items = [m for m in items if (m["sender"] == "user" and m["id"] <= cutoff) or (m["sender"] == "orion" and m.get("reply_to", m["id"]) < cutoff)]
        items.sort(key=lambda m: (m.get("reply_to", m["id"]), 1 if m["sender"] == "orion" else 0))
        return items[-limit:]

    def job(self, kind, label):
        job_id = uuid.uuid4().hex
        now = time.time()
        with self.lock, self.connection() as db:
            db.execute("INSERT INTO jobs(id,kind,label,status,created,updated) VALUES (?,?,?,'queued',?,?)", (job_id, kind, label[:140], now, now))
        return job_id

    def update(self, job_id, status, current=None, result=None):
        with self.lock, self.connection() as db:
            if current is None:
                current = 1 if status == "completed" else 0
            db.execute("UPDATE jobs SET status=?,current=?,result=COALESCE(?,result),updated=? WHERE id=?", (status, current, json.dumps(result, ensure_ascii=False) if result is not None else None, time.time(), job_id))

    def jobs(self, limit=100):
        with self.connection() as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM jobs ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
        return [{**dict(r), "result": json.loads(r["result"])} for r in rows]

    def usage(self, provider, model, data, seconds):
        incoming = data.get("input_tokens", data.get("prompt_tokens", 0)) or 0
        outgoing = data.get("output_tokens", data.get("completion_tokens", 0)) or 0
        with self.lock, self.connection() as db:
            db.execute("INSERT INTO usage(provider,model,input_tokens,output_tokens,seconds,created) VALUES (?,?,?,?,?,?)", (provider, model, incoming, outgoing, seconds, time.time()))

    def statistics(self):
        with self.connection() as db:
            usage = db.execute("SELECT COUNT(*),COALESCE(SUM(input_tokens),0),COALESCE(SUM(output_tokens),0),COALESCE(AVG(seconds),0) FROM usage").fetchone()
            counts = dict(db.execute("SELECT sender,COUNT(*) FROM messages GROUP BY sender").fetchall())
            jobs = dict(db.execute("SELECT status,COUNT(*) FROM jobs GROUP BY status").fetchall())
        return {"api_calls": usage[0], "input_tokens": usage[1], "output_tokens": usage[2], "average_seconds": round(usage[3], 2), "messages": counts, "jobs": jobs, "cost_usd": None, "cost_note": "Faktiki xərc üçün provayderin istifadə panelinə bax."}
