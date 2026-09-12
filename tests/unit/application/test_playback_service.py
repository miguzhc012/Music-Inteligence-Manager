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
    SQLiteReleaseRepository,
    SQLiteResolutionRepository,
    SQLiteQueueRepository,
    SQLitePlaybackStateRepository,
)
from mim.mcm.application.source_resolvers import LocalSourceResolver, ResolverChain
from mim.mcm.application.resolution_service import ResolutionService, ResolutionConfig
from mim.mcm.application.release_service import ReleaseService
from mim.mcm.application.playback_service import PlaybackService, MutagenAudioBackend
from mim.mcm.domain.identity import Identity
from mim.mcm.domain.version import Version
from mim.mcm.domain.source import Source, SourceType
from mim.mcm.domain.library import LibraryEntry, FileStatus
from mim.mcm.domain.release import Release, ReleaseTrack, ReleaseType
from mim.mcm.domain.resolution import Resolution, Evidence, EvidenceType
from mim.mcm.domain.playback import QueueItem, PlaybackConfig, PlaybackState, PlaybackPosition, RepeatMode, ShuffleMode
from mim.mcm.domain.confidence import Confidence
from mim.mcm.domain.availability import Availability, AvailabilityStatus


@pytest.fixture
def full_setup():
    """Setup completo com todos os repositórios."""
    tmp_db = tempfile.NamedTemporaryFile(delete=False).name
    db = create_database(tmp_db)
    conn = db._conn
    
    identity_repo = SQLiteIdentityRepository(conn)
    version_repo = SQLiteVersionRepository(conn)
    source_repo = SQLiteSourceRepository(conn)
    library_repo = SQLiteLibraryEntryRepository(conn)
    release_repo = SQLiteReleaseRepository(conn)
    resolution_repo = SQLiteResolutionRepository(conn)
    queue_repo = SQLiteQueueRepository(conn)
    state_repo = SQLitePlaybackStateRepository(conn)
    
    yield {
        "db": db,
        "conn": conn,
        "identity_repo": identity_repo,
        "version_repo": version_repo,
        "source_repo": source_repo,
        "library_repo": library_repo,
        "release_repo": release_repo,
        "resolution_repo": resolution_repo,
        "queue_repo": queue_repo,
        "state_repo": state_repo,
    }
    
    db.close()
    os.unlink(tmp_db)


def test_playback_domain_entities():
    """Testa entidades de domínio de playback."""
    # PlaybackState enum
    assert PlaybackState.PLAYING.value == "playing"
    assert PlaybackState.PAUSED.value == "paused"
    
    # RepeatMode enum
    assert RepeatMode.OFF.value == "off"
    assert RepeatMode.ONE.value == "one"
    assert RepeatMode.ALL.value == "all"
    
    # ShuffleMode enum
    assert ShuffleMode.OFF.value == "off"
    assert ShuffleMode.ON.value == "on"
    
    # PlaybackPosition
    pos = PlaybackPosition(current_ms=5000, duration_ms=10000)
    assert pos.progress == 0.5
    
    pos_zero = PlaybackPosition()
    assert pos_zero.progress == 0.0
    
    # PlaybackConfig
    config = PlaybackConfig(volume=0.8, repeat_mode=RepeatMode.ALL)
    assert config.volume == 0.8
    assert config.repeat_mode == RepeatMode.ALL
    
    # QueueItem
    item = QueueItem(
        id="q1",
        version_id="v1",
        source_id="s1",
        position=0,
        added_at="2024-01-01T00:00:00Z",
    )
    assert item.position == 0


def test_queue_repository_crud(full_setup):
    """Testa CRUD do QueueRepository."""
    queue_repo = full_setup["queue_repo"]
    identity_repo = full_setup["identity_repo"]
    version_repo = full_setup["version_repo"]
    source_repo = full_setup["source_repo"]
    
    # Setup hierarchy
    identity_repo.add(Identity(id="id1", title="T", artist="A"))
    version_repo.add(Version(id="v1", identity_id="id1", label="O"))
    source_repo.add(Source(id="s1", version_id="v1", source_type=SourceType.LOCAL))
    
    # Add items
    item1 = QueueItem(id="q1", version_id="v1", source_id="s1", position=0, added_at="2024-01-01T00:00:00Z")
    item2 = QueueItem(id="q2", version_id="v1", source_id="s1", position=1, added_at="2024-01-01T00:00:01Z")
    
    queue_repo.add(item1)
    queue_repo.add(item2)
    
    # Get queue
    queue = queue_repo.get_queue()
    assert len(queue) == 2
    assert queue[0].id == "q1"
    assert queue[1].id == "q2"
    
    # Get single item
    fetched = queue_repo.get("q1")
    assert fetched is not None
    assert fetched.id == "q1"
    
    # Reorder
    queue_repo.reorder("q2", 0)
    queue = queue_repo.get_queue()
    assert queue[0].id == "q2"
    assert queue[1].id == "q1"
    
    # Remove
    queue_repo.remove("q1")
    queue = queue_repo.get_queue()
    assert len(queue) == 1
    assert queue[0].id == "q2"
    
    # Clear
    queue_repo.clear()
    queue = queue_repo.get_queue()
    assert len(queue) == 0


def test_playback_state_repository(full_setup):
    """Testa PlaybackStateRepository."""
    state_repo = full_setup["state_repo"]
    
    # Default state
    assert state_repo.get_state() == PlaybackState.STOPPED
    assert state_repo.get_position() == PlaybackPosition()
    assert state_repo.get_config() == PlaybackConfig()
    
    # Set state
    state_repo.set_state(PlaybackState.PLAYING)
    assert state_repo.get_state() == PlaybackState.PLAYING
    
    # Set position
    pos = PlaybackPosition(current_ms=10000, duration_ms=30000)
    state_repo.set_position(pos)
    fetched_pos = state_repo.get_position()
    assert fetched_pos.current_ms == 10000
    assert fetched_pos.duration_ms == 30000
    
    # Set config
    config = PlaybackConfig(
        volume=0.5,
        repeat_mode=RepeatMode.ALL,
        shuffle_mode=ShuffleMode.ON,
        crossfade_ms=5000,
        gapless=False,
    )
    state_repo.set_config(config)
    fetched_config = state_repo.get_config()
    assert fetched_config.volume == 0.5
    assert fetched_config.repeat_mode == RepeatMode.ALL
    assert fetched_config.shuffle_mode == ShuffleMode.ON
    assert fetched_config.crossfade_ms == 5000
    assert fetched_config.gapless is False


def test_mutagen_audio_backend():
    """Testa MutagenAudioBackend (básico sem arquivo real)."""
    backend = MutagenAudioBackend()
    
    assert backend.state == PlaybackState.STOPPED
    assert backend.current_source_id is None
    
    # Test volume clamping
    backend.set_volume(1.5)
    assert backend._volume == 1.0
    
    backend.set_volume(-0.5)
    assert backend._volume == 0.0
    
    # Test seek clamping
    backend._duration = 100000
    backend.seek(150000)
    assert backend._position == 100000
    
    backend.seek(-1000)
    assert backend._position == 0
    
    # Test callbacks
    callback_called = []
    def on_end():
        callback_called.append(True)
    
    backend.on_end(on_end)
    backend._on_end_callback()
    assert len(callback_called) == 1


def test_playback_service_basic(full_setup):
    """Testa PlaybackService básico."""
    identity_repo = full_setup["identity_repo"]
    version_repo = full_setup["version_repo"]
    source_repo = full_setup["source_repo"]
    library_repo = full_setup["library_repo"]
    queue_repo = full_setup["queue_repo"]
    state_repo = full_setup["state_repo"]
    
    # Setup hierarchy
    identity_repo.add(Identity(id="id1", title="Test", artist="Artist"))
    version_repo.add(Version(id="v1", identity_id="id1", label="Track 1"))
    source_repo.add(Source(id="s1", version_id="v1", source_type=SourceType.LOCAL))
    library_repo.add(LibraryEntry(id="s1", path="/fake/path.mp3", status=FileStatus.PRESENT))
    
    backend = MutagenAudioBackend()
    playback_service = PlaybackService(
        queue_repo=queue_repo,
        state_repo=state_repo,
        source_repo=source_repo,
        library_repo=library_repo,
        audio_backend=backend,
    )
    
    # Add to queue
    item = playback_service.add_to_queue("v1", "s1")
    assert item.version_id == "v1"
    assert item.source_id == "s1"
    assert item.position == 0
    
    queue = playback_service.get_queue()
    assert len(queue) == 1
    
    # Play
    playback_service.play()
    assert backend.state == PlaybackState.PLAYING
    assert backend.current_source_id == "s1"
    
    # Pause
    playback_service.pause()
    assert backend.state == PlaybackState.PAUSED
    
    # Resume
    playback_service.play()
    assert backend.state == PlaybackState.PLAYING
    
    # Stop
    playback_service.stop()
    assert backend.state == PlaybackState.STOPPED
    assert playback_service._current_queue_item is None


def test_playback_service_queue_navigation(full_setup):
    """Testa navegação na fila."""
    identity_repo = full_setup["identity_repo"]
    version_repo = full_setup["version_repo"]
    source_repo = full_setup["source_repo"]
    library_repo = full_setup["library_repo"]
    queue_repo = full_setup["queue_repo"]
    state_repo = full_setup["state_repo"]
    
    # Setup multiple tracks
    identity_repo.add(Identity(id="id1", title="Album", artist="Artist"))
    version_repo.add(Version(id="v1", identity_id="id1", label="Track 1"))
    version_repo.add(Version(id="v2", identity_id="id1", label="Track 2"))
    version_repo.add(Version(id="v3", identity_id="id1", label="Track 3"))
    source_repo.add(Source(id="s1", version_id="v1", source_type=SourceType.LOCAL))
    source_repo.add(Source(id="s2", version_id="v2", source_type=SourceType.LOCAL))
    source_repo.add(Source(id="s3", version_id="v3", source_type=SourceType.LOCAL))
    library_repo.add(LibraryEntry(id="s1", path="/fake/track1.mp3", status=FileStatus.PRESENT))
    library_repo.add(LibraryEntry(id="s2", path="/fake/track2.mp3", status=FileStatus.PRESENT))
    library_repo.add(LibraryEntry(id="s3", path="/fake/track3.mp3", status=FileStatus.PRESENT))
    
    backend = MutagenAudioBackend()
    playback_service = PlaybackService(
        queue_repo=queue_repo,
        state_repo=state_repo,
        source_repo=source_repo,
        library_repo=library_repo,
        audio_backend=backend,
    )
    
    # Add multiple items
    playback_service.add_to_queue("v1", "s1")
    playback_service.add_to_queue("v2", "s2")
    playback_service.add_to_queue("v3", "s3")
    
    # Play first
    playback_service.play()
    assert playback_service._current_queue_item.position == 0
    assert backend.current_source_id == "s1"
    
    # Next
    next_item = playback_service.move_to_next()
    assert next_item is not None
    assert next_item.position == 1
    assert backend.current_source_id == "s2"
    
    # Next again
    next_item = playback_service.move_to_next()
    assert next_item is not None
    assert next_item.position == 2
    assert backend.current_source_id == "s3"
    
    # Next at end (no repeat)
    next_item = playback_service.move_to_next()
    assert next_item is None
    
    # Previous
    prev_item = playback_service.move_to_previous()
    assert prev_item is not None
    assert prev_item.position == 1


def test_playback_service_repeat_modes(full_setup):
    """Testa modos de repeat."""
    identity_repo = full_setup["identity_repo"]
    version_repo = full_setup["version_repo"]
    source_repo = full_setup["source_repo"]
    library_repo = full_setup["library_repo"]
    queue_repo = full_setup["queue_repo"]
    state_repo = full_setup["state_repo"]
    
    identity_repo.add(Identity(id="id1", title="T", artist="A"))
    version_repo.add(Version(id="v1", identity_id="id1", label="T1"))
    version_repo.add(Version(id="v2", identity_id="id1", label="T2"))
    source_repo.add(Source(id="s1", version_id="v1", source_type=SourceType.LOCAL))
    source_repo.add(Source(id="s2", version_id="v2", source_type=SourceType.LOCAL))
    library_repo.add(LibraryEntry(id="s1", path="/f1.mp3", status=FileStatus.PRESENT))
    library_repo.add(LibraryEntry(id="s2", path="/f2.mp3", status=FileStatus.PRESENT))
    
    backend = MutagenAudioBackend()
    playback_service = PlaybackService(
        queue_repo=queue_repo,
        state_repo=state_repo,
        source_repo=source_repo,
        library_repo=library_repo,
        audio_backend=backend,
    )
    
    playback_service.add_to_queue("v1", "s1")
    playback_service.add_to_queue("v2", "s2")
    playback_service.play()
    
    # Repeat ONE
    mode = playback_service.toggle_repeat()
    assert mode == RepeatMode.ONE
    
    next_item = playback_service.move_to_next()
    assert next_item is not None
    assert next_item.position == 0  # Same track
    assert backend.current_source_id == "s1"
    
    # Repeat ALL
    mode = playback_service.toggle_repeat()
    assert mode == RepeatMode.ALL
    
    # Go to last track (one call from v1 pos 0 -> v2 pos 1)
    next_item = playback_service.move_to_next()
    assert next_item is not None
    assert next_item.position == 1
    assert backend.current_source_id == "s2"
    
    # Next should wrap to first
    next_item = playback_service.move_to_next()
    assert next_item is not None
    assert next_item.position == 0
    assert backend.current_source_id == "s1"
    
    # Repeat OFF
    mode = playback_service.toggle_repeat()
    assert mode == RepeatMode.OFF


def test_playback_service_shuffle(full_setup):
    """Testa modo shuffle."""
    identity_repo = full_setup["identity_repo"]
    version_repo = full_setup["version_repo"]
    source_repo = full_setup["source_repo"]
    library_repo = full_setup["library_repo"]
    queue_repo = full_setup["queue_repo"]
    state_repo = full_setup["state_repo"]
    
    identity_repo.add(Identity(id="id1", title="T", artist="A"))
    version_repo.add(Version(id="v1", identity_id="id1", label="T1"))
    version_repo.add(Version(id="v2", identity_id="id1", label="T2"))
    source_repo.add(Source(id="s1", version_id="v1", source_type=SourceType.LOCAL))
    source_repo.add(Source(id="s2", version_id="v2", source_type=SourceType.LOCAL))
    library_repo.add(LibraryEntry(id="s1", path="/f1.mp3", status=FileStatus.PRESENT))
    library_repo.add(LibraryEntry(id="s2", path="/f2.mp3", status=FileStatus.PRESENT))
    
    backend = MutagenAudioBackend()
    playback_service = PlaybackService(
        queue_repo=queue_repo,
        state_repo=state_repo,
        source_repo=source_repo,
        library_repo=library_repo,
        audio_backend=backend,
    )
    
    playback_service.add_to_queue("v1", "s1")
    playback_service.add_to_queue("v2", "s2")
    playback_service.play()
    
    # Toggle shuffle ON
    mode = playback_service.toggle_shuffle()
    assert mode == ShuffleMode.ON
    
    # Toggle shuffle OFF
    mode = playback_service.toggle_shuffle()
    assert mode == ShuffleMode.OFF


def test_playback_service_volume_seek(full_setup):
    """Testa volume e seek."""
    identity_repo = full_setup["identity_repo"]
    version_repo = full_setup["version_repo"]
    source_repo = full_setup["source_repo"]
    library_repo = full_setup["library_repo"]
    queue_repo = full_setup["queue_repo"]
    state_repo = full_setup["state_repo"]
    
    identity_repo.add(Identity(id="id1", title="T", artist="A"))
    version_repo.add(Version(id="v1", identity_id="id1", label="T1"))
    source_repo.add(Source(id="s1", version_id="v1", source_type=SourceType.LOCAL))
    library_repo.add(LibraryEntry(id="s1", path="/f1.mp3", status=FileStatus.PRESENT))
    
    backend = MutagenAudioBackend()
    playback_service = PlaybackService(
        queue_repo=queue_repo,
        state_repo=state_repo,
        source_repo=source_repo,
        library_repo=library_repo,
        audio_backend=backend,
    )
    
    playback_service.add_to_queue("v1", "s1")
    playback_service.play()
    
    # Volume
    playback_service.set_volume(0.5)
    assert backend._volume == 0.5
    
    playback_service.set_volume(1.5)  # Clamped
    assert backend._volume == 1.0
    
    # Seek
    backend._duration = 100000
    playback_service.seek(50000)
    assert backend._position == 50000
    
    # State persistence check
    pos = state_repo.get_position()
    assert pos.current_ms == 50000


def test_playback_service_get_state(full_setup):
    """Testa get_current_state."""
    identity_repo = full_setup["identity_repo"]
    version_repo = full_setup["version_repo"]
    source_repo = full_setup["source_repo"]
    library_repo = full_setup["library_repo"]
    queue_repo = full_setup["queue_repo"]
    state_repo = full_setup["state_repo"]
    
    identity_repo.add(Identity(id="id1", title="T", artist="A"))
    version_repo.add(Version(id="v1", identity_id="id1", label="T1"))
    source_repo.add(Source(id="s1", version_id="v1", source_type=SourceType.LOCAL))
    library_repo.add(LibraryEntry(id="s1", path="/f1.mp3", status=FileStatus.PRESENT))
    
    backend = MutagenAudioBackend()
    playback_service = PlaybackService(
        queue_repo=queue_repo,
        state_repo=state_repo,
        source_repo=source_repo,
        library_repo=library_repo,
        audio_backend=backend,
    )
    
    playback_service.add_to_queue("v1", "s1")
    playback_service.play()
    
    state = playback_service.get_current_state()
    
    assert state["state"] == "playing"
    assert "position" in state
    assert "duration" in state
    assert "volume" in state
    assert "current_item" in state
    assert "queue" in state
    assert "config" in state
    assert state["current_item"].version_id == "v1"
    assert len(state["queue"]) == 1