"""Each durable reviewer approval applies to one immutable run snapshot."""
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from screening import ROOT


@contextmanager
def database():
    path = Path(os.getenv("RECRUITMENT_DB", ROOT / ".local/runs.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    try:
        with db:
            db.execute("""CREATE TABLE IF NOT EXISTS runs
                       (id TEXT PRIMARY KEY, snapshot TEXT NOT NULL, approved_at TEXT)""")
            yield db
    finally:
        db.close()


def save(snapshot):
    run_id = uuid4().hex
    snapshot["created"] = datetime.now(timezone.utc).isoformat()
    with database() as db:
        db.execute("INSERT INTO runs VALUES (?, ?, NULL)", (run_id, json.dumps(snapshot)))
    return run_id


def read(run_id):
    with database() as db:
        row = db.execute("SELECT snapshot, approved_at FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        raise KeyError(run_id)
    return dict(**json.loads(row[0]), id=run_id, approved_at=row[1])


def approve(run_id, token):
    secret = os.getenv("RECRUITMENT_REVIEWER_KEY", "")
    if len(secret) < 24 or not secrets.compare_digest(secret.encode(), token.encode()):
        raise PermissionError("Reviewer authentication required.")
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT snapshot, approved_at FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise KeyError(run_id)
        if json.loads(row[0])["decision"]["validated"] != "eligible":
            raise ValueError("The evidence does not support shortlisting.")
        if row[1] is None:
            db.execute("UPDATE runs SET approved_at=? WHERE id=?",
                       (datetime.now(timezone.utc).isoformat(), run_id))
