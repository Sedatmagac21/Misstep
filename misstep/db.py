"""One SQLite connection shared safely by the web server's worker threads."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path


class Result:
    """Rows already read under the lock, with the parts of a cursor the code uses."""

    def __init__(self, cur: sqlite3.Cursor):
        self.rows = cur.fetchall() if cur.description else []
        self.lastrowid = cur.lastrowid

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows

    def __iter__(self):
        return iter(self.rows)


class Database:
    def __init__(self, path: Path | str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.RLock()

    def execute(self, sql: str, params=()) -> Result:
        with self.lock:
            return Result(self.conn.execute(sql, params))

    def executemany(self, sql: str, rows) -> None:
        with self.lock:
            self.conn.executemany(sql, rows)

    def executescript(self, sql: str) -> None:
        with self.lock:
            self.conn.executescript(sql)

    def commit(self) -> None:
        with self.lock:
            self.conn.commit()


_OPEN: dict[str, Database] = {}
_OPEN_LOCK = threading.Lock()


def connect(path: Path | str) -> Database:
    """The accounts and the progress store share one connection per database file."""
    key = str(Path(path).resolve())
    with _OPEN_LOCK:
        if key not in _OPEN:
            _OPEN[key] = Database(key)
        return _OPEN[key]
