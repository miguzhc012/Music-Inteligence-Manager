import sqlite3


def up(db_path: str) -> None:
    """Migração para adicionar tabelas de playback (queue, state, config)."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    # Tabela de queue
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS playback_queue (
            id TEXT PRIMARY KEY,
            version_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            added_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Tabela de estado de playback
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS playback_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Tabela de configuração de playback
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS playback_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    db.commit()
    db.close()


def down(db_path: str) -> None:
    """Desfaz a migração (DROP tables)."""
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("DROP TABLE IF EXISTS playback_queue")
    cursor.execute("DROP TABLE IF EXISTS playback_state")
    cursor.execute("DROP TABLE IF EXISTS playback_config")
    db.commit()
    db.close()