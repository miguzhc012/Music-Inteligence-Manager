import tempfile
import os
import sqlite3
import pytest

from mim.mcm.application.audio_extraction import (
    AudioExtractionApplicationService,
)
from mim.mcm.infrastructure.audio_extraction import (
    SQLiteAudioMetadataRepository,
)
from mim.mcm.domain.audio_metadata import AudioExtractionService, AudioMetadata


def create_temp_audio_file():
    """Create a proper MP3 file with valid ID3 header for testing."""
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    # Write a proper ID3v2 header (ID3 + version 2.3.0 + flags + size)
    # ID3v2.3.0: ID3 + 03 00 + 00 00 00 00 (size 0 means no extended header)
    id3_header = b"ID3\x03\x00\x00\x00\x00\x00"
    # Add some minimal frames to make it valid
    # TIT2 (title) frame: "TIT2" + size + flags + data
    title_frame = b"TIT2\x00\x00\x00\x08Test Song\x00"
    # Add a minimal MP3 frame (frame sync + header + minimal data)
    # Frame sync (0xFFE) + header + minimal data
    mp3_frame = b"\xff\xfb\x90\x00" + b"\x00" * 100
    tmp.write(id3_header + title_frame + mp3_frame)
    tmp.close()
    return tmp.name


def test_application_service_extract():
    """Test AudioExtractionApplicationService."""
    temp_audio_file = create_temp_audio_file()
    try:
        service = AudioExtractionApplicationService()
        metadata = service.extract(temp_audio_file)
        assert isinstance(metadata, AudioMetadata)
        assert metadata.path == temp_audio_file
    finally:
        if os.path.exists(temp_audio_file):
            os.unlink(temp_audio_file)


def test_application_service_cache():
    """Test that application-level caching works."""
    temp_audio_file = create_temp_audio_file()
    try:
        service = AudioExtractionApplicationService(enable_cache=True, max_cache_size=10)
        metadata1 = service.extract(temp_audio_file)
        metadata2 = service.extract(temp_audio_file)
        assert metadata1 is metadata2  # Should be same object due to lru_cache
    finally:
        if os.path.exists(temp_audio_file):
            os.unlink(temp_audio_file)


def test_sqlite_repository():
    """Test SQLiteAudioMetadataRepository."""
    temp_audio_file = create_temp_audio_file()
    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp_db.close()
    conn = sqlite3.connect(tmp_db.name)
    try:
        repo = SQLiteAudioMetadataRepository(conn)
        service = AudioExtractionApplicationService()
        
        # First call should extract and save
        metadata1 = repo.get_or_extract(temp_audio_file, service)
        assert isinstance(metadata1, AudioMetadata)
        
        # Second call should return cached (equivalent object)
        metadata2 = repo.get_or_extract(temp_audio_file, service)
        assert isinstance(metadata2, AudioMetadata)
        assert metadata1.path == metadata2.path
        assert metadata1.codec == metadata2.codec
        assert metadata1.duration_ms == metadata2.duration_ms
        # Note: Not asserting identity because repository returns equivalent objects
        
        # Verify it's in DB
        cursor = conn.execute("SELECT COUNT(*) FROM audio_metadata_cache")
        count = cursor.fetchone()[0]
        assert count == 1
    finally:
        conn.close()
        if os.path.exists(tmp_db.name):
            os.unlink(tmp_db.name)
        if os.path.exists(temp_audio_file):
            os.unlink(temp_audio_file)


def test_file_hash():
    """Test file hash computation."""
    temp_audio_file = create_temp_audio_file()
    try:
        service = AudioExtractionApplicationService()
        hash1 = service.get_file_hash(temp_audio_file)
        hash2 = service.get_file_hash(temp_audio_file)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length
    finally:
        if os.path.exists(temp_audio_file):
            os.unlink(temp_audio_file)