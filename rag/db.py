"""SQLite connection helper.

AI-assisted: written with Claude Code (Anthropic); reviewed by the team.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from rag import config


def connect(db_path: Path | str = config.DB_PATH) -> sqlite3.Connection:
    """Open the database, enforce foreign keys, and make sure tables exist.

    SQLite ignores REFERENCES clauses unless foreign_keys is switched on for
    each connection, so we do it here, in the one place every module connects.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(config.SCHEMA_PATH.read_text())
    return conn
