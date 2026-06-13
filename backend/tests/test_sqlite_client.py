import sqlite3
from contextlib import closing

from app.config import Settings
from app.db.sqlite_client import get_connection, get_db_path, init_db


def table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {row["name"] for row in rows}


def test_db_path_uses_configured_data_dir(tmp_path):
    settings = Settings(data_dir=str(tmp_path))

    assert get_db_path(settings) == tmp_path / "sqlite" / "rag.db"


def test_init_db_creates_core_tables_and_document_dedupe_constraint(tmp_path):
    settings = Settings(data_dir=str(tmp_path))

    init_db(settings)

    assert get_db_path(settings).exists()

    with closing(get_connection(settings)) as conn, conn:
        assert {
            "knowledge_bases",
            "documents",
            "conversations",
            "messages",
        }.issubset(table_names(conn))

        conn.execute(
            """
            INSERT INTO knowledge_bases (id, name, created_at, updated_at)
            VALUES ('kb_1', 'Default', '2026-06-09T00:00:00', '2026-06-09T00:00:00')
            """
        )
        conn.execute(
            """
            INSERT INTO documents (
                id, kb_id, filename, file_type, file_size, file_hash, created_at
            )
            VALUES (
                'doc_1', 'kb_1', 'handbook.pdf', 'pdf', 128, 'same_hash',
                '2026-06-09T00:00:00'
            )
            """
        )

        try:
            conn.execute(
                """
                INSERT INTO documents (
                    id, kb_id, filename, file_type, file_size, file_hash, created_at
                )
                VALUES (
                    'doc_2', 'kb_1', 'copy.pdf', 'pdf', 128, 'same_hash',
                    '2026-06-09T00:00:00'
                )
                """
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("documents must be unique per kb_id and file_hash")


def test_init_db_closes_connection_after_schema_creation(tmp_path):
    settings = Settings(data_dir=str(tmp_path))
    db_path = get_db_path(settings)

    init_db(settings)

    db_path.unlink()

    assert not db_path.exists()


def test_init_db_explicitly_closes_connection(monkeypatch):
    from app.db import sqlite_client

    class SpyConnection:
        def __init__(self):
            self.closed = False
            self.transaction_exited = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            self.transaction_exited = True
            return False

        def executescript(self, script: str):
            self.script = script

        def close(self):
            self.closed = True

    spy_connection = SpyConnection()
    monkeypatch.setattr(
        sqlite_client,
        "get_connection",
        lambda app_settings=None: spy_connection,
    )

    sqlite_client.init_db(Settings())

    assert spy_connection.transaction_exited is True
    assert spy_connection.closed is True
