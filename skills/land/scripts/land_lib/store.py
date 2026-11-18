import contextlib
import hashlib
import json
import re
import sqlite3
from pathlib import Path

from .core import LandError, common_dir, stamp, state_home

SCHEMA = """
CREATE TABLE IF NOT EXISTS contract (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS lease (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, holder TEXT NOT NULL, paths TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('active', 'submitted', 'released')), expires TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS entry (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, holder TEXT NOT NULL, branch TEXT NOT NULL,
  sha TEXT NOT NULL, base TEXT NOT NULL, fingerprint TEXT NOT NULL, lease INTEGER NOT NULL REFERENCES lease(id),
  reviewer TEXT NOT NULL, title TEXT NOT NULL DEFAULT '', body TEXT NOT NULL DEFAULT '',
  state TEXT NOT NULL CHECK (state IN ('queued', 'landing', 'awaiting-merge', 'landed', 'bounced')),
  candidate TEXT NOT NULL DEFAULT '', landed TEXT NOT NULL DEFAULT '', pr TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '', UNIQUE (sha, holder));
CREATE TABLE IF NOT EXISTS attempt (
  id INTEGER PRIMARY KEY, at TEXT NOT NULL, base TEXT NOT NULL, candidate TEXT NOT NULL,
  entries TEXT NOT NULL, state TEXT NOT NULL CHECK (state IN ('publishing', 'published', 'abandoned')));
CREATE TABLE IF NOT EXISTS log (at TEXT NOT NULL, kind TEXT NOT NULL, id INTEGER NOT NULL, state TEXT NOT NULL, note TEXT NOT NULL);
"""


def store_dir(common):
    name = common.parent.name if common.name == ".git" else common.name.removesuffix(".git")
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return state_home() / "land" / f"{slug}-{hashlib.sha1(str(common).encode()).hexdigest()[:8]}"


def pin_ref(sha):
    return f"refs/landing/pins/{sha}"


def trunk_ref(contract):
    if contract["mode"] == "local":
        return f"refs/landing/{contract['trunk']}"
    return f"refs/remotes/{contract['remote']}/{contract['trunk']}"


class Store:
    def __init__(self, directory):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.dir / "land.db", timeout=60, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    @classmethod
    def for_repo(cls, path):
        common = common_dir(path)
        directory = store_dir(common)
        if not (directory / "land.db").exists():
            raise LandError(f"{common.parent} has no landing contract; run land.py init in it")
        store = cls(directory)
        if not store.contract:
            store.close()
            raise LandError(f"{common.parent} has no landing contract; run land.py init in it")
        return store

    @contextlib.contextmanager
    def tx(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield self.db
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    @property
    def contract(self):
        return {row["key"]: json.loads(row["value"]) for row in self.db.execute("SELECT key, value FROM contract")}

    def put(self, db, key, value):
        db.execute("INSERT OR REPLACE INTO contract VALUES (?, ?)", (key, json.dumps(value)))

    @property
    def repo(self):
        return Path(self.contract["repo"])

    def log(self, db, kind, ident, state, note=""):
        db.execute("INSERT INTO log VALUES (?, ?, ?, ?, ?)", (stamp(), kind, ident, state, note))

    def set_entry(self, db, ident, state, **fields):
        assignments = ", ".join(f"{key} = ?" for key in ["state", *fields])
        db.execute(f"UPDATE entry SET {assignments} WHERE id = ?", (state, *fields.values(), ident))
        self.log(db, "entry", ident, state, fields.get("note", ""))

    def entries(self, *states):
        marks = ",".join("?" * len(states))
        return list(self.db.execute(f"SELECT * FROM entry WHERE state IN ({marks}) ORDER BY id", states))

    def entry(self, ident):
        return self.db.execute("SELECT * FROM entry WHERE id = ?", (ident,)).fetchone()
