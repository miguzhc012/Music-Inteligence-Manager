import tempfile
import os
import pytest

from mim.mcm.infrastructure.sqlite_db import create_database
from mim.mcm.infrastructure.repositories import (
    SQLiteIdentityRepository,
    SQLiteVersionRepository,
    SQLiteSourceRepository,
    SQLiteHistoryRepository,
    SQLitePlaySessionRepository,
)
from mim.mcm.domain.identity import Identity
from mim.mcm.domain.version import Version
from mim.mcm.domain.source import Source, SourceType
from mim.mcm.domain.history import HistoryEvent, HistoryEventType, PlaySession, ListeningStats


@pytest.fixture
def history_setup():
    """Setup para testes de histórico."""
    tmp_db = tempfile.NamedTemporaryFile(delete=False).name
    db = create_database(tmp_db)
    conn = db._conn
    
    identity_repo = SQLiteIdentityRepository(conn)
    version_repo = SQLiteVersionRepository(conn)
    source_repo = SQLiteSourceRepository(conn)
    history_repo = SQLiteHistoryRepository(conn)
    session_repo = SQLitePlaySessionRepository(conn)
    
    # Setup hierarchy
    identity_repo.add(Identity(id="id1", title="Test Song", artist="Test Artist"))
    version_repo.add(Version(id="v1", identity_id="id1", label="Original"))
    source_repo.add(Source(id="s1", version_id="v1", source_type=SourceType.LOCAL))
    
    yield {
        "db": db,
        "conn": conn,
        "history_repo": history_repo,
        "session_repo": session_repo,
    }
    
    db.close()
    os.unlink(tmp_db)


def test_history_domain_entities():
    """Testa entidades de domínio de histórico."""
    event = HistoryEvent(
        id="e1",
        event_type=HistoryEventType.PLAY,
        version_id="v1",
        source_id="s1",
        device_id="dev1",
        session_id="sess1",
        timestamp="2026-09-12T00:00:00Z",
        position_ms=0,
        duration_ms=200000,
        metadata={"volume": 0.8},
    )
    
    assert event.id == "e1"
    assert event.event_type == HistoryEventType.PLAY
    assert event.version_id == "v1"
    assert event.metadata["volume"] == 0.8
    
    # ListeningStats
    stats = ListeningStats(
        version_id="v1",
        play_count=10,
        total_ms=2000000,
        skip_count=2,
        complete_count=8,
        last_played="2026-09-12T01:00:00Z",
        first_played="2026-09-12T00:00:00Z",
        avg_position_pct=0.9,
    )
    
    assert stats.completion_rate == 0.8
    assert stats.skip_rate == 0.2


def test_history_repository_crud(history_setup):
    """Testa CRUD do HistoryRepository."""
    repo = history_setup["history_repo"]
    
    event = HistoryEvent(
        id="e1",
        event_type=HistoryEventType.PLAY,
        version_id="v1",
        source_id="s1",
        device_id="dev1",
        session_id="sess1",
        timestamp="2026-09-12T00:00:00Z",
        position_ms=0,
        duration_ms=200000,
        metadata={"user_agent": "MIM-Client"},
    )
    
    repo.add(event)
    
    # Get
    fetched = repo.get("e1")
    assert fetched is not None
    assert fetched.id == "e1"
    assert fetched.event_type == HistoryEventType.PLAY
    assert fetched.metadata["user_agent"] == "MIM-Client"
    
    # Get by version
    by_version = repo.get_by_version("v1")
    assert len(by_version) == 1
    
    # Get by session
    by_session = repo.get_by_session("sess1")
    assert len(by_session) == 1
    
    # Get by device
    by_device = repo.get_by_device("dev1")
    assert len(by_device) == 1
    
    # Get by type
    by_type = repo.get_by_type(HistoryEventType.PLAY)
    assert len(by_type) == 1
    
    # Get recent
    recent = repo.get_recent()
    assert len(recent) == 1


def test_play_session_repository_crud(history_setup):
    """Testa CRUD do PlaySessionRepository."""
    repo = history_setup["session_repo"]
    
    session = PlaySession(
        id="sess1",
        device_id="dev1",
        started_at="2026-09-12T00:00:00Z",
        ended_at=None,
        total_tracks=0,
        total_listening_ms=0,
    )
    
    repo.add(session)
    
    # Get active
    active = repo.get_active("dev1")
    assert active is not None
    assert active.id == "sess1"
    assert active.is_active is True
    
    # Update
    updated = PlaySession(
        id="sess1",
        device_id="dev1",
        started_at="2026-09-12T00:00:00Z",
        ended_at="2026-09-12T01:00:00Z",
        total_tracks=15,
        total_listening_ms=3600000,
    )
    repo.update(updated)
    
    # Get after update
    fetched = repo.get("sess1")
    assert fetched.ended_at == "2026-09-12T01:00:00Z"
    assert fetched.total_tracks == 15
    assert fetched.is_active is False
    
    # List by device
    sessions = repo.list_by_device("dev1")
    assert len(sessions) == 1