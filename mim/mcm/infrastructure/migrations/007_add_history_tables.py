import sqlite3


def up(db_path: str) -> None:
    """Migração para adicionar tabelas de histórico e sessões."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    # Tabela de eventos de histórico
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS history_events (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL CHECK (event_type IN ('play', 'pause', 'skip', 'seek', 'volume_change', 'repeat_change', 'shuffle_change', 'queue_add', 'queue_remove', 'queue_reorder', 'resolution', 'download_start', 'download_complete', 'download_failed', 'cache_hit', 'cache_miss', 'lyrics_fetch', 'error')),
            version_id TEXT,
            source_id TEXT,
            device_id TEXT,
            session_id TEXT,
            timestamp TEXT NOT NULL,
            position_ms INTEGER,
            duration_ms INTEGER,
            metadata TEXT,  -- JSON
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_events_version ON history_events(version_id, timestamp)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_events_session ON history_events(session_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_events_device ON history_events(device_id, timestamp)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_events_type ON history_events(event_type, timestamp)"
    )

    # Tabela de sessões de reprodução
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS play_sessions (
            id TEXT PRIMARY KEY,
            device_id TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            total_tracks INTEGER NOT NULL DEFAULT 0,
            total_listening_ms INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_play_sessions_device ON play_sessions(device_id, started_at)"
    )

    # Tabela de estatísticas de escuta (materialized view / cache)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS listening_stats (
            version_id TEXT PRIMARY KEY,
            play_count INTEGER NOT NULL DEFAULT 0,
            total_ms INTEGER NOT NULL DEFAULT 0,
            skip_count INTEGER NOT NULL DEFAULT 0,
            complete_count INTEGER NOT NULL DEFAULT 0,
            last_played TEXT,
            first_played TEXT,
            avg_position_pct REAL NOT NULL DEFAULT 0.0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (version_id) REFERENCES versions(id)
        )
        """
    )

    db.commit()
    db.close()


def down(db_path: str) -> None:
    """Desfaz a migração (DROP tables)."""
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("DROP TABLE IF EXISTS listening_stats")
    cursor.execute("DROP TABLE IF EXISTS play_sessions")
    cursor.execute("DROP TABLE IF EXISTS history_events")
    db.commit()
    db.close()