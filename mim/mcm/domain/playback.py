from dataclasses import dataclass
from enum import Enum


class PlaybackState(str, Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"
    ERROR = "error"


class RepeatMode(str, Enum):
    OFF = "off"
    ONE = "one"
    ALL = "all"


class ShuffleMode(str, Enum):
    OFF = "off"
    ON = "on"


@dataclass(frozen=True)
class PlaybackPosition:
    """Posição atual de reprodução."""
    current_ms: int = 0
    duration_ms: int = 0
    
    @property
    def progress(self) -> float:
        if self.duration_ms == 0:
            return 0.0
        return min(self.current_ms / self.duration_ms, 1.0)


@dataclass(frozen=True)
class QueueItem:
    """Item na fila de reprodução."""
    id: str
    version_id: str
    source_id: str
    position: int  # Ordem na fila
    added_at: str  # ISO 8601


@dataclass(frozen=True)
class PlaybackConfig:
    """Configuração de reprodução."""
    volume: float = 1.0  # 0.0 a 1.0
    repeat_mode: RepeatMode = RepeatMode.OFF
    shuffle_mode: ShuffleMode = ShuffleMode.OFF
    crossfade_ms: int = 0
    gapless: bool = True