import sqlite3
from pathlib import Path
from backend.config import DB_PATH

SCHEMA_PATH = Path(__file__).parent / "models" / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """
    Additive migrations for columns that didn't exist in earlier schema versions.
    Each ALTER TABLE is wrapped in try/except because SQLite has no ADD COLUMN IF NOT EXISTS.
    Safe to run on every startup — no-ops if columns already exist.
    """
    migrations = [
        "ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE profiles ADD COLUMN shared INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE solicitations ADD COLUMN content_hash TEXT",
        "ALTER TABLE solicitation_capability_scores ADD COLUMN scored_hash TEXT",
    ]
    for sql in migrations:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass  # column already exists


def init_db() -> None:
    schema = SCHEMA_PATH.read_text()
    with get_connection() as conn:
        conn.executescript(schema)
        _migrate(conn)
