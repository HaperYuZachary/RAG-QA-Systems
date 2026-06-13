import sqlite3
from contextlib import closing
from pathlib import Path

from app.config import Settings, settings


def get_db_path(app_settings: Settings | None = None) -> Path:
    active_settings = app_settings or settings
    return Path(active_settings.data_dir) / "sqlite" / "rag.db"


def get_connection(app_settings: Settings | None = None) -> sqlite3.Connection:
    db_path = get_db_path(app_settings)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(app_settings: Settings | None = None) -> None:
    with closing(get_connection(app_settings)) as conn, conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS knowledge_bases (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                kb_id TEXT NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                file_hash TEXT NOT NULL,
                chunk_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'processing',
                error_msg TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(kb_id, file_hash)
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                kb_id TEXT NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
                title TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL
                    REFERENCES conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                token_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
