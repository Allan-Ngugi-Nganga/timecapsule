"""SQLite timeline index for fast queries across all snapshots.

Stores metadata for every snapshot: filepath, commit hash, message,
timestamp — bypasses git log for 100x faster queries."""

import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

CAPSULE_DIR = Path.home() / ".capsule"
DB_PATH = CAPSULE_DIR / "timeline.db"


class TimelineStore:
    """Thread-safe SQLite store for snapshot metadata."""

    def __init__(self, db_path: str | Path = DB_PATH):
        self._db_path = str(db_path)
        self._local = threading.local()
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT NOT NULL,
                hexsha TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp REAL NOT NULL,
                branch TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_filepath
            ON snapshots(filepath)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp
            ON snapshots(timestamp)
        """)
        conn.commit()
        conn.close()

    def record_snapshot(self, filepath: str, hexsha: str, message: str,
                        branch: str, timestamp: Optional[float] = None):
        ts = timestamp or datetime.now(timezone.utc).timestamp()
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            conn.execute(
                "INSERT INTO snapshots (filepath, hexsha, message, timestamp, branch) "
                "VALUES (?, ?, ?, ?, ?)",
                (os.path.normpath(filepath), hexsha, message, ts, branch),
            )
            conn.commit()
            conn.close()

    def get_timeline(self, filepath: str, limit: int = 50) -> list[dict]:
        """Get all snapshots for a file, newest first."""
        norm = os.path.normpath(filepath)
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM snapshots WHERE filepath = ? ORDER BY timestamp DESC LIMIT ?",
            (norm, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_all_files(self) -> list[dict]:
        """Get the latest snapshot for each tracked file."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT filepath, MAX(timestamp) as last_seen,
                   (SELECT message FROM snapshots s2
                    WHERE s2.filepath = snapshots.filepath
                    ORDER BY timestamp DESC LIMIT 1) as last_message
            FROM snapshots
            GROUP BY filepath
            ORDER BY last_seen DESC
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Search snapshot messages."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM snapshots WHERE message LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def total_snapshots(self) -> int:
        conn = sqlite3.connect(self._db_path)
        count = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        conn.close()
        return count

    def migrate_filepath(self, old_path: str, new_path: str, new_branch: str):
        """Migrate all snapshots from an old filepath to a new one.

        Called when a file is renamed. Updates the filepath and branch
        fields for all snapshots that belong to the old path, so the
        timeline browser shows the full history under the new name.
        """
        old_norm = os.path.normpath(old_path)
        new_norm = os.path.normpath(new_path)
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            conn.execute(
                "UPDATE snapshots SET filepath = ?, branch = ? WHERE filepath = ?",
                (new_norm, new_branch, old_norm),
            )
            conn.commit()
            conn.close()

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
