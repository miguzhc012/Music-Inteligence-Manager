from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Callable
from uuid import uuid4

from mim.mcm.domain.playback import (
    QueueItem, PlaybackConfig, PlaybackState, PlaybackPosition,
    RepeatMode, ShuffleMode
)
from mim.mcm.domain.ports import (
    QueueRepository, PlaybackStateRepository, AudioBackend,
    SourceRepository, LibraryEntryRepository
)
from mim.mcm.domain.source import Source, SourceType
from mim.mcm.domain.library import LibraryEntry, FileStatus
from mim.mcm.domain.resolution import Resolution, Evidence, EvidenceType
from mim.mcm.domain.confidence import Confidence
from mim.mcm.domain.availability import Availability, AvailabilityStatus
from mim.mcm.domain.version import Version


class MutagenAudioBackend(AudioBackend):
    """Backend de áudio usando mutagen + simpleaudio/pyglet (placeholder para integração real)."""
    
    def __init__(self):
        self._current_source_id: Optional[str] = None
        self._current_path: Optional[str] = None
        self._volume: float = 1.0
        self._position: int = 0
        self._duration: int = 0
        self._state: PlaybackState = PlaybackState.STOPPED
        self._on_end_callback: Optional[Callable] = None
        self._on_error_callback: Optional[Callable] = None

    def load(self, source_id: str, path: str) -> None:
        """Carrega arquivo de áudio."""
        self._current_source_id = source_id
        self._current_path = path
        self._state = PlaybackState.BUFFERING
        
        # Extract duration using mutagen
        try:
            from mutagen import File
            audio_file = File(path)
            if audio_file and hasattr(audio_file, 'info') and hasattr(audio_file.info, 'length'):
                self._duration = int(audio_file.info.length * 1000)
            else:
                self._duration = 0
        except Exception:
            self._duration = 0
        
        self._state = PlaybackState.PLAYING

    def play(self) -> None:
        self._state = PlaybackState.PLAYING

    def pause(self) -> None:
        self._state = PlaybackState.PAUSED

    def stop(self) -> None:
        self._state = PlaybackState.STOPPED
        self._position = 0

    def seek(self, position_ms: int) -> None:
        self._position = max(0, min(position_ms, self._duration))

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, volume))

    def get_position(self) -> int:
        return self._position

    def get_duration(self) -> int:
        return self._duration

    def on_end(self, callback: Callable) -> None:
        self._on_end_callback = callback

    def on_error(self, callback: Callable) -> None:
        self._on_error_callback = callback
    
    @property
    def state(self) -> PlaybackState:
        return self._state
    
    @property
    def current_source_id(self) -> Optional[str]:
        return self._current_source_id


@dataclass
class PlaybackService:
    """Serviço de aplicação para gerenciar reprodução, fila e estado."""
    
    queue_repo: QueueRepository
    state_repo: PlaybackStateRepository
    source_repo: SourceRepository
    library_repo: LibraryEntryRepository
    audio_backend: AudioBackend
    
    # Estado em memória para controle de reprodução
    _current_queue_item: Optional[QueueItem] = field(default=None, init=False)
    _queue_version: int = field(default=0, init=False)
    
    def __post_init__(self):
        # Carrega estado persistido
        self._sync_from_repos()
        # Configura callbacks do backend
        self.audio_backend.on_end(self._on_track_end)
        self.audio_backend.on_error(self._on_track_error)
    
    def _sync_from_repos(self):
        """Sincroniza estado em memória com repositórios."""
        state = self.state_repo.get_state()
        position = self.state_repo.get_position()
        config = self.state_repo.get_config()
        
        self.audio_backend._state = state
        self.audio_backend._position = position.current_ms
        self.audio_backend.set_volume(config.volume)
    
    # === Queue Management ===
    
    def add_to_queue(self, version_id: str, source_id: str) -> QueueItem:
        """Adiciona item ao final da fila."""
        queue = self.queue_repo.get_queue()
        position = len(queue)
        
        item = QueueItem(
            id=str(uuid4()),
            version_id=version_id,
            source_id=source_id,
            position=position,
            added_at=datetime.now().isoformat() + "Z",
        )
        
        self.queue_repo.add(item)
        self._queue_version += 1
        return item
    
    def get_queue(self) -> List[QueueItem]:
        """Retorna fila atual ordenada."""
        return self.queue_repo.get_queue()
    
    def remove_from_queue(self, item_id: str) -> None:
        """Remove item da fila."""
        self.queue_repo.remove(item_id)
        self._reindex_queue()
        self._queue_version += 1
    
    def clear_queue(self) -> None:
        """Limpa toda a fila."""
        self.queue_repo.clear()
        self._queue_version += 1
    
    def reorder_queue(self, item_id: str, new_position: int) -> None:
        """Reordena item na fila."""
        self.queue_repo.reorder(item_id, new_position)
        self._reindex_queue()
        self._queue_version += 1
    
    def _reindex_queue(self):
        """Reindexa posições após remoção/reordenação."""
        queue = self.queue_repo.get_queue()
        for idx, item in enumerate(queue):
            if item.position != idx:
                self.queue_repo.reorder(item.id, idx)
    
    def move_to_next(self) -> Optional[QueueItem]:
        """Avança para próxima faixa na fila."""
        queue = self.get_queue()
        if not queue:
            return None
        
        current_pos = self._get_current_queue_position()
        next_pos = current_pos + 1
        
        config = self.state_repo.get_config()
        if config.repeat_mode == RepeatMode.ONE:
            return self._current_queue_item
        
        if next_pos >= len(queue):
            if config.repeat_mode == RepeatMode.ALL:
                next_pos = 0
            else:
                return None
        
        if config.shuffle_mode == ShuffleMode.ON:
            import random
            next_pos = random.randrange(len(queue))
        
        return self._play_queue_item(queue[next_pos])
    
    def move_to_previous(self) -> Optional[QueueItem]:
        """Volta para faixa anterior na fila."""
        queue = self.get_queue()
        if not queue:
            return None
        
        current_pos = self._get_current_queue_position()
        prev_pos = current_pos - 1
        
        if prev_pos < 0:
            return None
        
        return self._play_queue_item(queue[prev_pos])
    
    def _get_current_queue_position(self) -> int:
        if self._current_queue_item:
            return self._current_queue_item.position
        return -1
    
    # === Playback Control ===
    
    def play(self) -> None:
        """Inicia ou retoma reprodução."""
        if self._current_queue_item is None:
            # Tenta tocar primeiro item da fila
            queue = self.get_queue()
            if queue:
                self._play_queue_item(queue[0])
            return
        
        self.audio_backend.play()
        self.state_repo.set_state(PlaybackState.PLAYING)
    
    def pause(self) -> None:
        """Pausa reprodução."""
        self.audio_backend.pause()
        self.state_repo.set_state(PlaybackState.PAUSED)
    
    def stop(self) -> None:
        """Para reprodução."""
        self.audio_backend.stop()
        self.state_repo.set_state(PlaybackState.STOPPED)
        self._current_queue_item = None
    
    def seek(self, position_ms: int) -> None:
        """Busca posição na faixa atual."""
        self.audio_backend.seek(position_ms)
        pos = PlaybackPosition(current_ms=position_ms, duration_ms=self.audio_backend.get_duration())
        self.state_repo.set_position(pos)
    
    def set_volume(self, volume: float) -> None:
        """Define volume (0.0 a 1.0)."""
        self.audio_backend.set_volume(volume)
        config = self.state_repo.get_config()
        self.state_repo.set_config(PlaybackConfig(
            volume=volume,
            repeat_mode=config.repeat_mode,
            shuffle_mode=config.shuffle_mode,
            crossfade_ms=config.crossfade_ms,
            gapless=config.gapless,
        ))
    
    def toggle_shuffle(self) -> ShuffleMode:
        """Alterna modo shuffle."""
        config = self.state_repo.get_config()
        new_mode = ShuffleMode.ON if config.shuffle_mode == ShuffleMode.OFF else ShuffleMode.OFF
        self.state_repo.set_config(PlaybackConfig(
            volume=config.volume,
            repeat_mode=config.repeat_mode,
            shuffle_mode=new_mode,
            crossfade_ms=config.crossfade_ms,
            gapless=config.gapless,
        ))
        return new_mode
    
    def toggle_repeat(self) -> RepeatMode:
        """Cicla modo repeat: OFF -> ONE -> ALL -> OFF."""
        config = self.state_repo.get_config()
        if config.repeat_mode == RepeatMode.OFF:
            new_mode = RepeatMode.ONE
        elif config.repeat_mode == RepeatMode.ONE:
            new_mode = RepeatMode.ALL
        else:
            new_mode = RepeatMode.OFF
        
        self.state_repo.set_config(PlaybackConfig(
            volume=config.volume,
            repeat_mode=new_mode,
            shuffle_mode=config.shuffle_mode,
            crossfade_ms=config.crossfade_ms,
            gapless=config.gapless,
        ))
        return new_mode
    
    def get_current_state(self) -> dict:
        """Retorna estado atual completo."""
        return {
            "state": self.audio_backend.state.value,
            "position": self.audio_backend.get_position(),
            "duration": self.audio_backend.get_duration(),
            "volume": self.audio_backend._volume,
            "current_item": self._current_queue_item,
            "queue": self.get_queue(),
            "config": self.state_repo.get_config(),
        }
    
    def _play_queue_item(self, item: QueueItem) -> QueueItem:
        """Carrega e toca um item da fila."""
        source = self.source_repo.get(item.source_id)
        if not source:
            raise ValueError(f"Source {item.source_id} not found")
        
        entry = self.library_repo.get_by_id(source.id)
        if not entry or entry.status != FileStatus.PRESENT:
            raise ValueError(f"File not present for source {item.source_id}")
        
        self.audio_backend.load(item.source_id, entry.path)
        self._current_queue_item = item
        
        # Atualiza posição
        pos = PlaybackPosition(current_ms=0, duration_ms=self.audio_backend.get_duration())
        self.state_repo.set_position(pos)
        self.state_repo.set_state(PlaybackState.PLAYING)
        
        return item
    
    def _on_track_end(self):
        """Callback quando faixa termina."""
        self.move_to_next()
    
    def _on_track_error(self, error: Exception):
        """Callback quando há erro na reprodução."""
        self.state_repo.set_state(PlaybackState.ERROR)
        # Tenta próxima faixa
        self.move_to_next()


@dataclass
class ResolutionApplicationService:
    """Serviço de aplicação que integra resolução + materialização + playback."""
    
    resolution_service: 'ResolutionService'  # Forward reference
    playback_service: PlaybackService
    source_repo: SourceRepository
    library_repo: LibraryEntryRepository
    
    def resolve_and_queue(self, version_id: str) -> Optional[QueueItem]:
        """Resolve uma versão e adiciona à fila de reprodução."""
        resolution = self.resolution_service.resolve_version(version_id)
        
        if not resolution.is_resolved():
            return None
        
        source_id = resolution.get_best_source_id()
        if not source_id:
            return None
        
        return self.playback_service.add_to_queue(version_id, source_id)
    
    def resolve_and_play(self, version_id: str) -> bool:
        """Resolve uma versão e inicia reprodução imediata."""
        item = self.resolve_and_queue(version_id)
        if item:
            self.playback_service.play()
            return True
        return False