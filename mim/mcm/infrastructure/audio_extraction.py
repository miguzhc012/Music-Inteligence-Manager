"""
Infrastructure service for audio extraction.
Provides persistent caching of extracted audio metadata.
"""
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Optional

from mim.mcm.application.audio_extraction import AudioExtractionApplicationService, AudioMetadata


class SQLiteAudioMetadataRepository:
    """
    Persistent cache for audio metadata using SQLite.
    Stores extracted metadata keyed by file hash.
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._ensure_table()

    def _ensure_table(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audio_metadata_cache (
                file_hash TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                extracted_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._conn.commit()

    def get(self, file_path: str) -> Optional[AudioMetadata]:
        """Get cached metadata if available and file hasn't changed."""
        file_hash = self._get_file_hash(file_path)
        row = self._conn.execute(
            "SELECT metadata_json FROM audio_metadata_cache WHERE file_hash = ? AND file_path = ?",
            (file_hash, file_path),
        ).fetchone()
        if row:
            try:
                data = json.loads(row[0])
                return AudioMetadata(**data)
            except Exception:
                return None
        return None

    def save(self, metadata: AudioMetadata) -> None:
        """Save metadata to cache."""
        file_hash = self._get_file_hash(metadata.path)
        metadata_json = json.dumps(metadata.__dict__, default=str)
        self._conn.execute(
            "INSERT OR REPLACE INTO audio_metadata_cache (file_hash, file_path, metadata_json) VALUES (?, ?, ?)",
            (file_hash, metadata.path, metadata_json),
        )
        self._conn.commit()

    def get_or_extract(self, path: str, extractor: AudioExtractionApplicationService) -> AudioMetadata:
        """Get from cache or extract and save."""
        cached = self.get(path)
        if cached:
            return cached
        metadata = extractor.extract(path)
        self.save(metadata)
        return metadata

    def _get_file_hash(self, path: str) -> str:
        """Compute SHA256 hash of file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()


class AudioExtractionInfrastructureService:
    """
    Infrastructure service that combines extraction with persistent caching.
    """

    def __init__(self, db_path: str = "library.db"):
        self._extractor = AudioExtractionApplicationService()
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def extract(self, path: str) -> AudioMetadata:
        """Extract audio metadata with persistent caching."""
        conn = self._get_connection()
        repo = SQLiteAudioMetadataRepository(conn)
        return repo.get_or_extract(path, self._extractor)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None