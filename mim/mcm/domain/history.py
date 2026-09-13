from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


class HistoryEventType(str, Enum):
    """Tipos de eventos no histórico."""
    PLAY = "play"
    PAUSE = "pause"
    SKIP = "skip"
    SEEK = "seek"
    VOLUME_CHANGE = "volume_change"
    REPEAT_CHANGE = "repeat_change"
    SHUFFLE_CHANGE = "shuffle_change"
    QUEUE_ADD = "queue_add"
    QUEUE_REMOVE = "queue_remove"
    QUEUE_REORDER = "queue_reorder"
    RESOLUTION = "resolution"
    DOWNLOAD_START = "download_start"
    DOWNLOAD_COMPLETE = "download_complete"
    DOWNLOAD_FAILED = "download_failed"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    LYRICS_FETCH = "lyrics_fetch"
    ERROR = "error"


@dataclass(frozen=True)
class HistoryEvent:
    """Evento individual no histórico de reprodução."""
    id: str = ""
    event_type: HistoryEventType = HistoryEventType.PLAY
    version_id: str | None = None
    source_id: str | None = None
    device_id: str | None = None
    session_id: str | None = None
    timestamp: str = ""
    position_ms: int | None = None
    duration_ms: int | None = None
    metadata: dict | None = None  # Dados extras específicos do evento
    
    def __post_init__(self):
        if not self.id:
            object.__setattr__(self, 'id', str(uuid4()))
        if not self.timestamp:
            object.__setattr__(self, 'timestamp', datetime.now().isoformat() + "Z")
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})


@dataclass(frozen=True)
class PlaySession:
    """Sessão de reprodução contínua."""
    id: str
    device_id: str
    started_at: str
    ended_at: str | None = None
    total_tracks: int = 0
    total_listening_ms: int = 0
    
    @property
    def is_active(self) -> bool:
        return self.ended_at is None


@dataclass(frozen=True)
class ListeningStats:
    """Estatísticas agregadas de escuta."""
    version_id: str
    play_count: int = 0
    total_ms: int = 0
    skip_count: int = 0
    complete_count: int = 0
    last_played: str | None = None
    first_played: str | None = None
    avg_position_pct: float = 0.0  # 0.0 a 1.0
    
    @property
    def completion_rate(self) -> float:
        if self.play_count == 0:
            return 0.0
        return self.complete_count / self.play_count
    
    @property
    def skip_rate(self) -> float:
        if self.play_count == 0:
            return 0.0
        return self.skip_count / self.play_count