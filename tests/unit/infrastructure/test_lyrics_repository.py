import tempfile
import os
import pytest
from datetime import datetime

from mim.mcm.infrastructure.sqlite_db import create_database
from mim.mcm.infrastructure.repositories import (
    SQLiteIdentityRepository,
    SQLiteVersionRepository,
    SQLiteSourceRepository,
    SQLiteLibraryEntryRepository,
    SQLiteLyricsRepository,
)
from mim.mcm.domain.identity import Identity
from mim.mcm.domain.version import Version
from mim.mcm.domain.source import Source, SourceType
from mim.mcm.domain.lyrics import Lyrics, LyricsLine, LyricsType, LyricsSource, LyricsSearchQuery


@pytest.fixture
def lyrics_setup():
    """Setup para testes de letras."""
    tmp_db = tempfile.NamedTemporaryFile(delete=False).name
    db = create_database(tmp_db)
    conn = db._conn
    
    identity_repo = SQLiteIdentityRepository(conn)
    version_repo = SQLiteVersionRepository(conn)
    source_repo = SQLiteSourceRepository(conn)
    library_repo = SQLiteLibraryEntryRepository(conn)
    lyrics_repo = SQLiteLyricsRepository(conn)
    
    yield {
        "db": db,
        "conn": conn,
        "identity_repo": identity_repo,
        "version_repo": version_repo,
        "source_repo": source_repo,
        "library_repo": library_repo,
        "lyrics_repo": lyrics_repo,
    }
    
    db.close()
    os.unlink(tmp_db)


def test_lyrics_domain_entities():
    """Testa entidades de domínio de letras."""
    # LyricsType enum
    assert LyricsType.SYNCED.value == "synced"
    assert LyricsType.UNSYNCED.value == "unsynced"
    
    # LyricsSource enum
    assert LyricsSource.LOCAL.value == "local"
    assert LyricsSource.EMBEDDED.value == "embedded"
    assert LyricsSource.PROVIDER.value == "provider"
    assert LyricsSource.USER.value == "user"
    
    # LyricsLine
    line = LyricsLine(timestamp_ms=5000, text="Hello world", translation="Olá mundo")
    assert line.timestamp_ms == 5000
    assert line.text == "Hello world"
    assert line.translation == "Olá mundo"
    
    # Lyrics unsynced
    lyrics = Lyrics(
        version_id="v1",
        lyrics_type=LyricsType.UNSYNCED,
        source=LyricsSource.PROVIDER,
        content="Full lyrics text here...",
        lines=[],
    )
    assert lyrics.is_synced is False
    
    # Lyrics synced
    synced_lyrics = Lyrics(
        version_id="v1",
        lyrics_type=LyricsType.SYNCED,
        source=LyricsSource.LOCAL,
        content="",
        lines=[
            LyricsLine(timestamp_ms=0, text="Line 1"),
            LyricsLine(timestamp_ms=5000, text="Line 2"),
            LyricsLine(timestamp_ms=10000, text="Line 3"),
        ],
    )
    assert synced_lyrics.is_synced is True
    assert synced_lyrics.get_line_at(3000).text == "Line 1"
    assert synced_lyrics.get_line_at(5000).text == "Line 2"
    assert synced_lyrics.get_line_at(7000).text == "Line 2"
    assert synced_lyrics.get_line_at(10000).text == "Line 3"
    assert synced_lyrics.get_line_at(15000).text == "Line 3"
    assert synced_lyrics.get_next_line(3000).text == "Line 2"
    assert synced_lyrics.get_next_line(10000) is None
    
    # LyricsSearchQuery
    query = LyricsSearchQuery(
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        duration_ms=180000,
        isrc="USRC12345678",
    )
    assert query.title == "Test Song"
    assert query.artist == "Test Artist"


def test_lyrics_repository_crud(lyrics_setup):
    """Testa CRUD do LyricsRepository."""
    identity_repo = lyrics_setup["identity_repo"]
    version_repo = lyrics_setup["version_repo"]
    source_repo = lyrics_setup["source_repo"]
    lyrics_repo = lyrics_setup["lyrics_repo"]
    
    # Setup hierarchy
    identity_repo.add(Identity(id="id1", title="Test Song", artist="Test Artist"))
    version_repo.add(Version(id="v1", identity_id="id1", label="Original"))
    source_repo.add(Source(id="s1", version_id="v1", source_type=SourceType.LOCAL))
    
    # Create synced lyrics
    lyrics = Lyrics(
        version_id="v1",
        lyrics_type=LyricsType.SYNCED,
        source=LyricsSource.LOCAL,
        content="",
        lines=[
            LyricsLine(timestamp_ms=0, text="First line", translation="Primeira linha"),
            LyricsLine(timestamp_ms=5000, text="Second line", translation="Segunda linha"),
            LyricsLine(timestamp_ms=10000, text="Third line", translation="Terceira linha"),
        ],
        language="en",
        fetched_at=datetime.now().isoformat() + "Z",
    )
    
    lyrics_repo.add(lyrics)
    
    # Get lyrics
    fetched = lyrics_repo.get("v1")
    assert fetched is not None
    assert fetched.version_id == "v1"
    assert fetched.lyrics_type == LyricsType.SYNCED
    assert fetched.source == LyricsSource.LOCAL
    assert fetched.language == "en"
    assert len(fetched.lines) == 3
    assert fetched.lines[0].text == "First line"
    assert fetched.lines[0].translation == "Primeira linha"
    assert fetched.lines[1].text == "Second line"
    assert fetched.lines[2].text == "Third line"
    assert fetched.is_synced is True
    
    # Update lyrics (add more lines)
    updated_lyrics = Lyrics(
        version_id="v1",
        lyrics_type=LyricsType.SYNCED,
        source=LyricsSource.LOCAL,
        content="",
        lines=[
            LyricsLine(timestamp_ms=0, text="First line", translation="Primeira linha"),
            LyricsLine(timestamp_ms=5000, text="Second line", translation="Segunda linha"),
            LyricsLine(timestamp_ms=10000, text="Third line", translation="Terceira linha"),
            LyricsLine(timestamp_ms=15000, text="Fourth line", translation="Quarta linha"),
        ],
        language="en",
        fetched_at=datetime.now().isoformat() + "Z",
    )
    lyrics_repo.update(updated_lyrics)
    
    fetched = lyrics_repo.get("v1")
    assert len(fetched.lines) == 4
    assert fetched.lines[3].text == "Fourth line"
    
    # Test unsynced lyrics
    unsynced = Lyrics(
        version_id="v2",
        lyrics_type=LyricsType.UNSYNCED,
        source=LyricsSource.PROVIDER,
        content="Full lyrics content without timestamps...",
        lines=[],
        language="en",
        fetched_at=datetime.now().isoformat() + "Z",
    )
    
    version_repo.add(Version(id="v2", identity_id="id1", label="Remix"))
    lyrics_repo.add(unsynced)
    
    fetched_unsynced = lyrics_repo.get("v2")
    assert fetched_unsynced is not None
    assert fetched_unsynced.lyrics_type == LyricsType.UNSYNCED
    assert fetched_unsynced.content == "Full lyrics content without timestamps..."
    assert fetched_unsynced.is_synced is False
    assert len(fetched_unsynced.lines) == 0
    
    # Delete
    lyrics_repo.delete("v1")
    assert lyrics_repo.get("v1") is None
    # v2 should still exist
    assert lyrics_repo.get("v2") is not None
    
    # Non-existent
    assert lyrics_repo.get("nonexistent") is None


def test_lyrics_search_query():
    """Testa LyricsSearchQuery."""
    query = LyricsSearchQuery(
        title="Bohemian Rhapsody",
        artist="Queen",
        album="A Night at the Opera",
        duration_ms=354000,
        isrc="GBARL0300012",
    )
    
    assert query.title == "Bohemian Rhapsody"
    assert query.artist == "Queen"
    assert query.album == "A Night at the Opera"
    assert query.duration_ms == 354000
    assert query.isrc == "GBARL0300012"
    
    # Minimal query
    minimal = LyricsSearchQuery(title="Song", artist="Artist")
    assert minimal.title == "Song"
    assert minimal.artist == "Artist"
    assert minimal.album is None
    assert minimal.duration_ms is None
    assert minimal.isrc is None