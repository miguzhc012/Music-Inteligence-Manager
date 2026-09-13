import sqlite3


def up(db_path: str) -> None:
    """Migração para adicionar tabelas de discovery e recommendation."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    # Tabela de search matches
    cursor.execute(
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
        )
        """
    )

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_matches_identity ON search_matches(identity_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_matches_version ON search_matches(version_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_matches_quality ON search_matches(quality, score)")

    # Tabela de acoustic profiles
    cursor.execute(
        """
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
        )
        """
    )

    # Tabela de recommendations
    cursor.execute(
        """
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
        )
        """
    )

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendations_source ON recommendations(source_version_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendations_identity ON recommendations(target_identity_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendations_type ON recommendations(type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendations_recent ON recommendations(created_at DESC)")

    # Tabela de user taste profiles
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_taste_profiles (
            user_id TEXT PRIMARY KEY,
            favorite_artists TEXT NOT NULL DEFAULT '[]',
            favorite_genres TEXT NOT NULL DEFAULT '[]',
            listening_count INTEGER NOT NULL DEFAULT 0,
            total_ms_listened INTEGER NOT NULL DEFAULT 0,
            skip_rate REAL NOT NULL DEFAULT 0.0,
            repeat_rate REAL NOT NULL DEFAULT 0.0,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Tabela de audio features
    cursor.execute(
        """
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
        )
        """
    )

    db.commit()
    db.close()


def down(db_path: str) -> None:
    """Desfaz a migração (DROP tables)."""
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("DROP TABLE IF EXISTS audio_features")
    cursor.execute("DROP TABLE IF EXISTS user_taste_profiles")
    cursor.execute("DROP TABLE IF EXISTS recommendations")
    cursor.execute("DROP TABLE IF EXISTS acoustic_profiles")
    cursor.execute("DROP TABLE IF EXISTS search_matches")
    db.commit()
    db.close()