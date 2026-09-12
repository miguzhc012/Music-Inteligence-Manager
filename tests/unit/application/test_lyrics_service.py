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
from mim.mcm.application.lyrics_service import LyricsService, LocalLyricsProvider
from mim.mcm.domain.identity import Identity
from mim.mcm.domain.version import Version
from mim.mcm.domain.source import Source, SourceType
from mim.mcm.domain.library import LibraryEntry, FileStatus
from mim.mcm.domain.lyrics import Lyrics, LyricsLine, LyricsType, LyricsSource, LyricsSearchQuery


@pytest.fixture
def lyrics_service_setup():
    """Setup completo para LyricsService."""
    tmp_db = tempfile.NamedTemporaryFile(delete=False).name
    db = create_database(tmp_db)
    conn = db._conn
    
    identity_repo = SQLiteIdentityRepository(conn)
    version_repo = SQLiteVersionRepository(conn)
    source_repo = SQLiteSourceRepository(conn)
    library_repo = SQLiteLibraryEntryRepository(conn)
    lyrics_repo = SQLiteLyricsRepository(conn)
    
    # Setup hierarchy
    identity_repo.add(Identity(id="id1", title="Test Song", artist="Test Artist"))
    version_repo.add(Version(id="v1", identity_id="id1", label="Original"))
    version_repo.add(Version(id="v2", identity_id="id1", label="Remix"))
    source_repo.add(Source(id="s1", version_id="v1", source_type=SourceType.LOCAL))
    source_repo.add(Source(id="s2", version_id="v2", source_type=SourceType.LOCAL))
    library_repo.add(LibraryEntry(id="s1", path="/music/test.mp3", status=FileStatus.PRESENT))
    library_repo.add(LibraryEntry(id="s2", path="/music/test_remix.mp3", status=FileStatus.PRESENT))
    
    local_provider = LocalLyricsProvider(library_repo)
    
    service = LyricsService(
        lyrics_repo=lyrics_repo,
        providers=[local_provider],
        version_repo=version_repo,
        identity_repo=identity_repo,
    )
    
    yield {
        "db": db,
        "conn": conn,
        "identity_repo": identity_repo,
        "version_repo": version_repo,
        "source_repo": source_repo,
        "library_repo": library_repo,
        "lyrics_repo": lyrics_repo,
        "service": service,
    }
    
    db.close()
    os.unlink(tmp_db)


def test_lyrics_service_get_lyrics_not_found(lyrics_service_setup):
    """Testa busca de letras inexistentes."""
    service = lyrics_service_setup["service"]
    
    # No lyrics cached, no providers return anything
    lyrics = service.get_lyrics("v1")
    assert lyrics is None


def test_lyrics_service_get_lyrics_cached(lyrics_service_setup):
    """Testa busca de letras já em cache."""
    lyrics_repo = lyrics_service_setup["lyrics_repo"]
    service = lyrics_service_setup["service"]
    
    # Pre-populate cache
    cached_lyrics = Lyrics(
        version_id="v1",
        lyrics_type=LyricsType.SYNCED,
        source=LyricsSource.LOCAL,
        content="",
        lines=[
            LyricsLine(timestamp_ms=0, text="Cached line 1"),
            LyricsLine(timestamp_ms=5000, text="Cached line 2"),
        ],
        language="en",
        fetched_at=datetime.now().isoformat() + "Z",
    )
    lyrics_repo.add(cached_lyrics)
    
    # Should return cached
    lyrics = service.get_lyrics("v1")
    assert lyrics is not None
    assert lyrics.source == LyricsSource.LOCAL
    assert len(lyrics.lines) == 2
    assert lyrics.lines[0].text == "Cached line 1"


def test_lyrics_service_save_lyrics(lyrics_service_setup):
    """Testa salvamento de letras (manual/user)."""
    service = lyrics_service_setup["service"]
    
    lyrics = Lyrics(
        version_id="v1",
        lyrics_type=LyricsType.UNSYNCED,
        source=LyricsSource.USER,
        content="User entered lyrics...",
        lines=[],
        language="en",
    )
    
    saved = service.save_lyrics("v1", lyrics)
    
    assert saved.version_id == "v1"
    assert saved.source == LyricsSource.USER
    assert saved.content == "User entered lyrics..."
    assert saved.language == "en"
    
    # Verify persisted
    fetched = service.lyrics_repo.get("v1")
    assert fetched is not None
    assert fetched.source == LyricsSource.USER
    assert fetched.content == "User entered lyrics..."


def test_lyrics_service_save_synced_lyrics(lyrics_service_setup):
    """Testa salvamento de letras sincronizadas."""
    service = lyrics_service_setup["service"]
    
    lyrics = Lyrics(
        version_id="v1",
        lyrics_type=LyricsType.SYNCED,
        source=LyricsSource.USER,
        content="",
        lines=[
            LyricsLine(timestamp_ms=0, text="Synced line 1", translation="Linha 1"),
            LyricsLine(timestamp_ms=3000, text="Synced line 2", translation="Linha 2"),
            LyricsLine(timestamp_ms=6000, text="Synced line 3", translation="Linha 3"),
        ],
        language="en",
    )
    
    saved = service.save_lyrics("v1", lyrics)
    
    assert saved.is_synced is True
    assert len(saved.lines) == 3
    assert saved.lines[0].translation == "Linha 1"
    
    # Test get_current_line
    current = service.get_current_line("v1", 1000)
    assert current is not None
    assert current.text == "Synced line 1"
    
    current = service.get_current_line("v1", 4000)
    assert current.text == "Synced line 2"
    
    current = service.get_current_line("v1", 10000)
    assert current.text == "Synced line 3"
    
    # Test get_next_line
    next_line = service.get_next_line("v1", 1000)
    assert next_line.text == "Synced line 2"
    
    next_line = service.get_next_line("v1", 6000)
    assert next_line is None


def test_lyrics_service_delete_lyrics(lyrics_service_setup):
    """Testa exclusão de letras."""
    lyrics_repo = lyrics_service_setup["lyrics_repo"]
    service = lyrics_service_setup["service"]
    
    # Add lyrics first
    lyrics = Lyrics(
        version_id="v1",
        lyrics_type=LyricsType.UNSYNCED,
        source=LyricsSource.PROVIDER,
        content="To be deleted",
        lines=[],
    )
    lyrics_repo.add(lyrics)
    
    # Verify exists
    assert lyrics_repo.get("v1") is not None
    
    # Delete
    service.delete_lyrics("v1")
    
    # Verify deleted
    assert lyrics_repo.get("v1") is None


def test_local_lyrics_provider_search(lyrics_service_setup):
    """Testa LocalLyricsProvider (stub)."""
    library_repo = lyrics_service_setup["library_repo"]
    provider = LocalLyricsProvider(library_repo)
    
    query = LyricsSearchQuery(title="Test", artist="Artist")
    results = provider.search(query)
    
    assert results == []  # Stub returns empty


def test_lyrics_service_multiple_versions(lyrics_service_setup):
    """Testa letras para múltiplas versões da mesma identity."""
    service = lyrics_service_setup["service"]
    
    # Save lyrics for v1
    lyrics_v1 = Lyrics(
        version_id="v1",
        lyrics_type=LyricsType.UNSYNCED,
        source=LyricsSource.USER,
        content="Original version lyrics",
        lines=[],
    )
    service.save_lyrics("v1", lyrics_v1)
    
    # Save different lyrics for v2 (remix)
    lyrics_v2 = Lyrics(
        version_id="v2",
        lyrics_type=LyricsType.UNSYNCED,
        source=LyricsSource.USER,
        content="Remix version lyrics",
        lines=[],
    )
    service.save_lyrics("v2", lyrics_v2)
    
    # Fetch both
    fetched_v1 = service.get_lyrics("v1")
    fetched_v2 = service.get_lyrics("v2")
    
    assert fetched_v1.content == "Original version lyrics"
    assert fetched_v2.content == "Remix version lyrics"
    assert fetched_v1.version_id == "v1"
    assert fetched_v2.version_id == "v2"