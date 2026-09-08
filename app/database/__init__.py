"""SQLite database package for IntelliGate AI AEGIS."""

from .db import get_connection, initialize_database

__all__ = ["get_connection", "initialize_database"]
