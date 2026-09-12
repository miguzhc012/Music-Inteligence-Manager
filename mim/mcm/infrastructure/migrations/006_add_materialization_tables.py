import sqlite3


def up(db_path: str) -> None:
    """Migração para adicionar tabelas de materialização e device storage."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    # Tabela de materializações
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS materializations (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            device_id TEXT,
            state TEXT NOT NULL CHECK (state IN ('unavailable', 'cached', 'downloaded')),
            file_path TEXT,
            quality TEXT NOT NULL CHECK (quality IN ('unknown', 'low', 'medium', 'high', 'lossless', 'hires')),
            format TEXT,
            bitrate INTEGER,
            sample_rate INTEGER,
            bit_depth INTEGER,
            file_size INTEGER,
            checksum TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES sources(id)
        )
        """
    )

    # Tabela de device storage
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS device_storage (
            device_id TEXT PRIMARY KEY,
            total_bytes INTEGER NOT NULL,
            free_bytes INTEGER NOT NULL,
            path TEXT NOT NULL,
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
    cursor.execute("DROP TABLE IF EXISTS materializations")
    cursor.execute("DROP TABLE IF EXISTS device_storage")
    db.commit()
    db.close()