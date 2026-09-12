import sqlite3


def up(db_path: str) -> None:
    """Migração para adicionar tabelas de letras."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    # Tabela de letras
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS lyrics (
            version_id TEXT PRIMARY KEY,
            lyrics_type TEXT NOT NULL CHECK (lyrics_type IN ('synced', 'unsynced')),
            source TEXT NOT NULL CHECK (source IN ('local', 'embedded', 'provider', 'user')),
            content TEXT NOT NULL,
            language TEXT,
            fetched_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (version_id) REFERENCES versions(id)
        )
        """
    )

    # Tabela de linhas de letras sincronizadas
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS lyrics_lines (
            id TEXT PRIMARY KEY,
            version_id TEXT NOT NULL,
            timestamp_ms INTEGER NOT NULL,
            text TEXT NOT NULL,
            translation TEXT,
            line_order INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (version_id) REFERENCES versions(id)
        )
        """
    )

    # Índice para busca ordenada
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_lyrics_lines_version_order ON lyrics_lines(version_id, line_order)"
    )

    db.commit()
    db.close()


def down(db_path: str) -> None:
    """Desfaz a migração (DROP tables)."""
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("DROP TABLE IF EXISTS lyrics_lines")
    cursor.execute("DROP TABLE IF EXISTS lyrics")
    db.commit()
    db.close()