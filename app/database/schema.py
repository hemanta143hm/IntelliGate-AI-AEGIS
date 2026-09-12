"""SQLite schema for AEGIS Phases 1-5."""

SCHEMA_STATEMENTS = (
    # Phase 1 tables
    """
    CREATE TABLE IF NOT EXISTS persons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        external_id TEXT UNIQUE,
        display_name TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cameras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        stream_uri TEXT,
        status TEXT NOT NULL DEFAULT 'offline',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (location_id) REFERENCES locations(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS zones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        camera_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (camera_id) REFERENCES cameras(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS attendance_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id INTEGER,
        zone_id INTEGER,
        started_at TEXT NOT NULL,
        ended_at TEXT,
        FOREIGN KEY (person_id) REFERENCES persons(id),
        FOREIGN KEY (zone_id) REFERENCES zones(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS security_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        camera_id INTEGER,
        zone_id INTEGER,
        event_type TEXT NOT NULL,
        confidence REAL,
        occurred_at TEXT NOT NULL,
        metadata TEXT,
        FOREIGN KEY (camera_id) REFERENCES cameras(id),
        FOREIGN KEY (zone_id) REFERENCES zones(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        security_event_id INTEGER,
        title TEXT NOT NULL,
        severity TEXT NOT NULL DEFAULT 'low',
        status TEXT NOT NULL DEFAULT 'open',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        resolved_at TEXT,
        FOREIGN KEY (security_event_id) REFERENCES security_events(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor TEXT NOT NULL,
        action TEXT NOT NULL,
        resource_type TEXT,
        resource_id INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        details TEXT
    )
    """,
    # Phase 5 attendance table
    """
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id INTEGER NOT NULL,
        person_name TEXT NOT NULL,
        location_id INTEGER,
        camera_id INTEGER,
        entry_time TEXT NOT NULL,
        exit_time TEXT,
        duration_seconds INTEGER,
        status TEXT NOT NULL DEFAULT 'PRESENT',
        confidence REAL DEFAULT 0.0,
        visit_count INTEGER DEFAULT 1,
        first_seen_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (person_id) REFERENCES persons(id),
        FOREIGN KEY (location_id) REFERENCES locations(id),
        FOREIGN KEY (camera_id) REFERENCES cameras(id)
    )
    """,
)

# Migration statements for backward compatibility
MIGRATION_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id INTEGER NOT NULL,
        person_name TEXT NOT NULL,
        location_id INTEGER,
        camera_id INTEGER,
        entry_time TEXT NOT NULL,
        exit_time TEXT,
        duration_seconds INTEGER,
        status TEXT NOT NULL DEFAULT 'PRESENT',
        confidence REAL DEFAULT 0.0,
        visit_count INTEGER DEFAULT 1,
        first_seen_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (person_id) REFERENCES persons(id),
        FOREIGN KEY (location_id) REFERENCES locations(id),
        FOREIGN KEY (camera_id) REFERENCES cameras(id)
    )
    """,
)
