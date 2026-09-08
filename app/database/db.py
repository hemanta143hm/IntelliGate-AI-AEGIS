"""SQLite connection and initialization helpers."""

import sqlite3
from pathlib import Path

from app.core.config import settings
from app.database.schema import SCHEMA_STATEMENTS


def get_connection(database_path: Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with foreign keys enabled."""

    path = Path(database_path or settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path | None = None) -> None:
    """Create the database file and all Phase 1 tables."""

    with get_connection(database_path) as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.commit()
