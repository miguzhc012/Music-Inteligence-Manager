import tempfile
import os
import pytest

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
    tmp.write(id3_header + title_frame)
    # Add a minimal MP3 frame (frame sync + header + minimal data)
    # Frame sync (0xFFE) + header + minimal data
    mp3_frame = b"\xff\xfb\x90\x00" + b"\x00" * 100
    tmp.write(mp3_frame)
    tmp.close()
    return tmp.name


def test_audio_metadata_extraction():
    """Test that AudioExtractionService can extract metadata."""
    temp_audio_file = create_temp_audio_file()
    try:
        service = AudioExtractionService()
        metadata = service.extract(temp_audio_file)
        assert isinstance(metadata, AudioMetadata)
        assert metadata.path == temp_audio_file
        assert metadata.codec is not None
        assert metadata.duration_ms >= 0
    finally:
        if os.path.exists(temp_audio_file):
            os.unlink(temp_audio_file)


def test_audio_metadata_to_dict():
    """Test to_dict conversion."""
    temp_audio_file = create_temp_audio_file()
    try:
        service = AudioExtractionService()
        metadata = service.extract(temp_audio_file)
        d = metadata.to_dict()
        assert isinstance(d, dict)
        assert "path" in d
        assert "codec" in d
        assert "format_label" in d
    finally:
        if os.path.exists(temp_audio_file):
            os.unlink(temp_audio_file)


def test_audio_extraction_cache():
    """Test that caching works."""
    temp_audio_file = create_temp_audio_file()
    try:
        service = AudioExtractionService(enable_cache=True, max_cache_size=10)
        metadata1 = service.extract(temp_audio_file)
        metadata2 = service.extract(temp_audio_file)
        # Should be same object due to lru_cache
        assert metadata1 is metadata2
    finally:
        if os.path.exists(temp_audio_file):
            os.unlink(temp_audio_file)


def test_audio_extraction_no_cache():
    """Test that disabling cache works."""
    temp_audio_file = create_temp_audio_file()
    try:
        service = AudioExtractionService(enable_cache=False)
        metadata1 = service.extract(temp_audio_file)
        metadata2 = service.extract(temp_audio_file)
        # Should be different instances
        assert metadata1 is not metadata2
        assert metadata1.path == metadata2.path
    finally:
        if os.path.exists(temp_audio_file):
            os.unlink(temp_audio_file)