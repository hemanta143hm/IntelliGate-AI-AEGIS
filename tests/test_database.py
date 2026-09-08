import sqlite3

from app.database.db import initialize_database
from app.database.schema import SCHEMA_STATEMENTS


def test_database_initializes_required_tables(tmp_path) -> None:
    database_path = tmp_path / "test.sqlite3"
    initialize_database(database_path)
    with sqlite3.connect(database_path) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    required = {"persons", "locations", "cameras", "zones", "attendance_sessions", "security_events", "incidents", "audit_logs"}
    assert required.issubset(tables)
    assert len(SCHEMA_STATEMENTS) == 8
