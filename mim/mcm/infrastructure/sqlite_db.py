import sqlite3
from pathlib import Path
from typing import Optional

from mim.mcm.domain.release import Release, ReleaseTrack, ReleaseType
from mim.mcm.domain.ports import ReleaseRepository


class SQLiteDatabase:
    """Gerenciador de conexão e migrações para SQLite."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._enable_foreign_keys()
        self._run_migrations()
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def _enable_foreign_keys(self) -> None:
        assert self._conn is not None
        self._conn.execute("PRAGMA foreign_keys = ON")

    def _run_migrations(self) -> None:
        assert self._conn is not None
        cursor = self._conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        current = cursor.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()[0] or 0

        # Migrations registry
        migrations = [
            (
                1,
                """
                CREATE TABLE IF NOT EXISTS library_entries (
                    id TEXT PRIMARY KEY,
                    path TEXT UNIQUE NOT NULL,
                    status TEXT NOT NULL
                        CHECK (status IN ('PRESENT', 'MISSING'))
                );
                CREATE TABLE IF NOT EXISTS identities (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS versions (
                    id TEXT PRIMARY KEY,
                    identity_id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    FOREIGN KEY (identity_id) REFERENCES identities(id)
                );
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    version_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    FOREIGN KEY (version_id) REFERENCES versions(id)
                );
                """
            ),
            (
                2,
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
                );
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
                );
                """
            ),
            (
                3,
                """
                CREATE TABLE IF NOT EXISTS resolutions (
                    resolution_id TEXT PRIMARY KEY,
                    version_id TEXT NOT NULL,
                    source_id TEXT,
                    confidence_value REAL NOT NULL,
                    availability_status TEXT NOT NULL CHECK (availability_status IN ('unknown', 'available', 'unavailable', 'stale')),
                    resolved_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (version_id) REFERENCES versions(id)
                );
                CREATE TABLE IF NOT EXISTS resolution_evidence (
                    id TEXT PRIMARY KEY,
                    resolution_id TEXT NOT NULL,
                    evidence_type TEXT NOT NULL CHECK (evidence_type IN ('metadata_match', 'acoustic_fingerprint', 'isrc_match', 'mbid_match', 'file_hash', 'user_confirmation', 'provider_assertion')),
                    weight REAL NOT NULL,
                    description TEXT,
                    source_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (resolution_id) REFERENCES resolutions(resolution_id)
                );
                """
            ),
            (
                4,
                """
                CREATE TABLE IF NOT EXISTS playback_queue (
                    id TEXT PRIMARY KEY,
                    version_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    added_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS playback_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS playback_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            ),
            (
                5,
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
                );
                CREATE TABLE IF NOT EXISTS lyrics_lines (
                    id TEXT PRIMARY KEY,
                    version_id TEXT NOT NULL,
                    timestamp_ms INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    translation TEXT,
                    line_order INTEGER NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (version_id) REFERENCES versions(id)
                );
                CREATE INDEX IF NOT EXISTS idx_lyrics_lines_version_order ON lyrics_lines(version_id, line_order);
                """
            ),
            (
                6,
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
                );
                CREATE TABLE IF NOT EXISTS device_storage (
                    device_id TEXT PRIMARY KEY,
                    total_bytes INTEGER NOT NULL,
                    free_bytes INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            ),
            (
                7,
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
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_history_events_version ON history_events(version_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_history_events_session ON history_events(session_id);
                CREATE INDEX IF NOT EXISTS idx_history_events_device ON history_events(device_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_history_events_type ON history_events(event_type, timestamp);
                CREATE TABLE IF NOT EXISTS play_sessions (
                    id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    total_tracks INTEGER NOT NULL DEFAULT 0,
                    total_listening_ms INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_play_sessions_device ON play_sessions(device_id, started_at);
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
                );
                """
            ),
            (
                8,
                """
                CREATE TABLE IF NOT EXISTS search_matches (
                    id TEXT PRIMARY KEY,
                    identity_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    version_id TEXT,
                    source_id TEXT,
                    release_id TEXT,
                    album TEXT,
                    quality TEXT NOT NULL CHECK (quality IN ('exact', 'high', 'medium', 'low', 'none')),
                    score REAL NOT NULL,
                    method TEXT NOT NULL CHECK (method IN ('title_match', 'artist_match', 'album_match', 'isrc_match', 'acoustic_fingerprint', 'file_hash', 'mbid_match', 'user_input', 'recommendation')),
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (identity_id) REFERENCES identities(id)
                );
                CREATE INDEX IF NOT EXISTS idx_search_matches_identity ON search_matches(identity_id);
                CREATE INDEX IF NOT EXISTS idx_search_matches_version ON search_matches(version_id);
                CREATE INDEX IF NOT EXISTS idx_search_matches_quality ON search_matches(quality, score);
                CREATE TABLE IF NOT EXISTS acoustic_profiles (
                    version_id TEXT PRIMARY KEY,
                    tempo_bpm REAL,
                    key TEXT,
                    mode TEXT,
                    duration_ms INTEGER,
                    energy REAL,
                    danceability REAL,
                    valence REAL,
                    audio_features TEXT,
                    fingerprint_hash TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (version_id) REFERENCES versions(id)
                );
                CREATE TABLE IF NOT EXISTS recommendations (
                    id TEXT PRIMARY KEY,
                    source_version_id TEXT,
                    target_identity_id TEXT,
                    target_version_id TEXT,
                    target_source_id TEXT,
                    type TEXT NOT NULL CHECK (type IN ('similar_artists', 'similar_tracks', 'based_on_history', 'trending', 'new_releases', 'collective_taste', 'radio_station', 'contextual')),
                    algorithm TEXT NOT NULL CHECK (algorithm IN ('cosine_similarity', 'jaccard_index', 'eucilean', 'cosine_audio', 'collaborative_filtering', 'content_based')),
                    similarity_score REAL NOT NULL,
                    confidence REAL NOT NULL,
                    context TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_version_id) REFERENCES versions(id),
                    FOREIGN KEY (target_identity_id) REFERENCES identities(id)
                );
                CREATE INDEX IF NOT EXISTS idx_recommendations_source ON recommendations(source_version_id);
                CREATE INDEX IF NOT EXISTS idx_recommendations_identity ON recommendations(target_identity_id);
                CREATE INDEX IF NOT EXISTS idx_recommendations_type ON recommendations(type);
                CREATE INDEX IF NOT EXISTS idx_recommendations_recent ON recommendations(created_at DESC);
                CREATE TABLE IF NOT EXISTS user_taste_profiles (
                    user_id TEXT PRIMARY KEY,
                    favorite_artists TEXT NOT NULL DEFAULT '[]',
                    favorite_genres TEXT NOT NULL DEFAULT '[]',
                    listening_count INTEGER NOT NULL DEFAULT 0,
                    total_ms_listened INTEGER NOT NULL DEFAULT 0,
                    skip_rate REAL NOT NULL DEFAULT 0.0,
                    repeat_rate REAL NOT NULL DEFAULT 0.0,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS audio_features (
                    version_id TEXT PRIMARY KEY,
                    tempo_bpm REAL,
                    key TEXT,
                    mode TEXT,
                    energy REAL,
                    danceability REAL,
                    valence REAL,
                    acousticness REAL,
                    instrumentalness REAL,
                    liveness REAL,
                    speechiness REAL,
                    duration_ms INTEGER,
                    analyzed_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (version_id) REFERENCES versions(id)
                );
                """
            )
        ]

        for version, sql_script in migrations:
            if version > current:
                for statement in sql_script.split(";"):
                    if statement.strip():
                        cursor.execute(statement)
                cursor.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (version,),
                )

        self._conn.commit()


def create_database(db_path: str) -> SQLiteDatabase:
    db = SQLiteDatabase(db_path)
    db.connect()
    return db
