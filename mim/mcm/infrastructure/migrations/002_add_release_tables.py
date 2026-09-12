import sqlite3
from pathlib import Path

from mim.mcm.domain.release import Release, ReleaseTrack, ReleaseType
from mim.mcm.domain.ports import ReleaseRepository


def up(db_path: str) -> None:
    """Migração para adicionar tabelas de Release e ReleaseTrack."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    # Cria tabela releases
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS releases (
            id TEXT PRIMARY KEY,
            identity_id TEXT NOT NULL,
            title TEXT NOT NULL,
            release_type TEXT NOT NULL CHECK (release_type IN ('album', 'single', 'ep', 'compilation', 'soundtrack', 'live', 'remix', 'other')),
            release_date TEXT NOT NULL,
            label TEXT,
            catalog_number TEXT,
            cover_url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (identity_id) REFERENCES versions(id)
        )
    )

    # Cria tabela release_tracks
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS release_tracks (
            id TEXT PRIMARY KEY,
            release_id TEXT NOT NULL,
            version_id TEXT NOT NULL,
            track_number INTEGER NOT NULL,
            disc_number INTEGER NOT NULL DEFAULT 1,
            duration_ms INTEGER,
            isrc TEXT,
            explicit INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (release_id) REFERENCES releases(id),
            FOREIGN KEY (version_id) REFERENCES versions(id)
        )
    )

    db.commit()
    db.close()


def down(db_path: str) -> None:
    """Desfaz a migração (DROP tables)."""
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("DROP TABLE IF EXISTS release_tracks")
    cursor.execute("DROP TABLE IF EXISTS releases")
    db.commit()
    db.close()
