from abc import ABC, abstractmethod

from .identity import Identity
from .version import Version
from .source import Source
from .library import LibraryEntry, FileStatus
from .release import Release, ReleaseTrack
from .resolution import Resolution
from .playback import QueueItem, PlaybackConfig, PlaybackState, PlaybackPosition
from .lyrics import Lyrics, LyricsSearchQuery, LyricsType, LyricsSource
from .materialization import Materialization, MaterializationState, MaterializationQuality, DeviceStorage
from .history import HistoryEvent, HistoryEventType, PlaySession, ListeningStats
from .discovery import SearchQuery, SearchMatch, DiscoveryMethod, MatchQuality, AcousticProfile
from .recommendation import Recommendation, RecommendationType, SimilarityAlgorithm, UserTasteProfile, AudioFeature


class IdentityRepository(ABC):
    @abstractmethod
    def get(self, identity_id: str) -> Identity: ...

    @abstractmethod
    def add(self, identity: Identity) -> None: ...

    @abstractmethod
    def get_by_title_and_artist(self, title: str, artist: str) -> list[Identity]: ...


class VersionRepository(ABC):
    @abstractmethod
    def get(self, version_id: str) -> Version: ...

    @abstractmethod
    def add(self, version: Version) -> None: ...

    @abstractmethod
    def get_by_identity(self, identity_id: str) -> list[Version]: ...


class SourceRepository(ABC):
    @abstractmethod
    def get(self, source_id: str) -> Source: ...

    @abstractmethod
    def add(self, source: Source) -> None: ...

    @abstractmethod
    def get_by_version(self, version_id: str) -> list[Source]: ...


class ReleaseRepository(ABC):
    """Repositório para Releases e ReleaseTracks."""
    @abstractmethod
    def get_release(self, release_id: str) -> Release | None: ...

    @abstractmethod
    def add_release(self, release: Release) -> None: ...

    @abstractmethod
    def get_tracks_by_release(self, release_id: str) -> list[ReleaseTrack]: ...

    @abstractmethod
    def add_track(self, track: ReleaseTrack) -> None: ...

    @abstractmethod
    def get_releases_by_identity(self, identity_id: str) -> list[Release]: ...


class ResolutionRepository(ABC):
    """Repositório para resoluções de Version -> Source."""
    @abstractmethod
    def get(self, resolution_id: str) -> Resolution | None: ...

    @abstractmethod
    def get_by_version(self, version_id: str) -> Resolution | None: ...

    @abstractmethod
    def add(self, resolution: Resolution) -> None: ...

    @abstractmethod
    def update(self, resolution: Resolution) -> None: ...


class IndexPublisher(ABC):
    """Publica o índice replicado do MCM para o MCL."""

    @abstractmethod
    def publish(self, entries: list) -> None: ...


class SourceResolver(ABC):
    """Contrato para resolução de Source a partir de uma Version. Sem implementação."""

    @abstractmethod
    def resolve(self, version_id: str) -> str | None: ...


class LibraryEntryRepository(ABC):
    @abstractmethod
    def add(self, entry: LibraryEntry) -> None: ...

    @abstractmethod
    def get_by_id(self, entry_id: str) -> LibraryEntry | None: ...

    @abstractmethod
    def get_by_path(self, path: str) -> LibraryEntry | None: ...

    @abstractmethod
    def update_status(self, entry_id: str, status: FileStatus) -> None: ...

    @abstractmethod
    def list_all(self) -> list[LibraryEntry]: ...


class QueueRepository(ABC):
    """Repositório para fila de reprodução."""
    @abstractmethod
    def add(self, item: QueueItem) -> None: ...

    @abstractmethod
    def get(self, item_id: str) -> QueueItem | None: ...

    @abstractmethod
    def get_queue(self) -> list[QueueItem]: ...

    @abstractmethod
    def remove(self, item_id: str) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def reorder(self, item_id: str, new_position: int) -> None: ...


class PlaybackStateRepository(ABC):
    """Repositório para estado de reprodução persistido."""
    @abstractmethod
    def get_state(self) -> PlaybackState: ...

    @abstractmethod
    def set_state(self, state: PlaybackState) -> None: ...

    @abstractmethod
    def get_position(self) -> PlaybackPosition: ...

    @abstractmethod
    def set_position(self, position: PlaybackPosition) -> None: ...

    @abstractmethod
    def get_config(self) -> PlaybackConfig: ...

    @abstractmethod
    def set_config(self, config: PlaybackConfig) -> None: ...


class AudioBackend(ABC):
    """Backend abstrato de reprodução de áudio."""
    @abstractmethod
    def load(self, source_id: str, path: str) -> None: ...

    @abstractmethod
    def play(self) -> None: ...

    @abstractmethod
    def pause(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def seek(self, position_ms: int) -> None: ...

    @abstractmethod
    def set_volume(self, volume: float) -> None: ...

    @abstractmethod
    def get_position(self) -> int: ...

    @abstractmethod
    def get_duration(self) -> int: ...

    @abstractmethod
    def on_end(self, callback) -> None: ...

    @abstractmethod
    def on_error(self, callback) -> None: ...


class LyricsRepository(ABC):
    """Repositório para letras."""
    @abstractmethod
    def get(self, version_id: str) -> Lyrics | None: ...

    @abstractmethod
    def add(self, lyrics: Lyrics) -> None: ...

    @abstractmethod
    def update(self, lyrics: Lyrics) -> None: ...

    @abstractmethod
    def delete(self, version_id: str) -> None: ...


class LyricsProvider(ABC):
    """Provedor externo de letras (LRCLIB, Genius, etc.)."""
    @abstractmethod
    def search(self, query: LyricsSearchQuery) -> list[Lyrics]: ...

    @abstractmethod
    def fetch_by_id(self, provider_id: str) -> Lyrics | None: ...


class MaterializationRepository(ABC):
    """Repositório para materializações (arquivos físicos de sources)."""
    @abstractmethod
    def get(self, source_id: str, device_id: str | None = None) -> Materialization | None: ...

    @abstractmethod
    def add(self, materialization: Materialization) -> None: ...

    @abstractmethod
    def update(self, materialization: Materialization) -> None: ...

    @abstractmethod
    def delete(self, source_id: str, device_id: str | None = None) -> None: ...

    @abstractmethod
    def get_by_device(self, device_id: str) -> list[Materialization]: ...

    @abstractmethod
    def get_available_for_source(self, source_id: str) -> list[Materialization]: ...


class DeviceStorageRepository(ABC):
    """Repositório para informações de armazenamento de dispositivos."""
    @abstractmethod
    def get(self, device_id: str) -> DeviceStorage | None: ...

    @abstractmethod
    def add(self, storage: DeviceStorage) -> None: ...

    @abstractmethod
    def update(self, storage: DeviceStorage) -> None: ...

    @abstractmethod
    def delete(self, device_id: str) -> None: ...

    @abstractmethod
    def list_all(self) -> list[DeviceStorage]: ...


class HistoryRepository(ABC):
    """Repositório para eventos de histórico."""
    @abstractmethod
    def add(self, event: HistoryEvent) -> None: ...

    @abstractmethod
    def get(self, event_id: str) -> HistoryEvent | None: ...

    @abstractmethod
    def get_by_version(self, version_id: str, limit: int = 100) -> list[HistoryEvent]: ...

    @abstractmethod
    def get_by_session(self, session_id: str) -> list[HistoryEvent]: ...

    @abstractmethod
    def get_by_device(self, device_id: str, limit: int = 100) -> list[HistoryEvent]: ...

    @abstractmethod
    def get_by_type(self, event_type: HistoryEventType, limit: int = 100) -> list[HistoryEvent]: ...

    @abstractmethod
    def get_recent(self, limit: int = 100) -> list[HistoryEvent]: ...

    @abstractmethod
    def get_stats(self, version_id: str) -> ListeningStats | None: ...


class PlaySessionRepository(ABC):
    """Repositório para sessões de reprodução."""
    @abstractmethod
    def add(self, session: PlaySession) -> None: ...

    @abstractmethod
    def get(self, session_id: str) -> PlaySession | None: ...

    @abstractmethod
    def get_active(self, device_id: str) -> PlaySession | None: ...

    @abstractmethod
    def update(self, session: PlaySession) -> None: ...

    @abstractmethod
    def list_by_device(self, device_id: str) -> list[PlaySession]: ...


class DiscoveryRepository(ABC):
    """Repositório para matches de descoberta."""
    @abstractmethod
    def save_match(self, match: SearchMatch) -> None: ...

    @abstractmethod
    def get_matches(self, identity_id: str) -> list[SearchMatch]: ...

    @abstractmethod
    def get_by_version(self, version_id: str) -> list[SearchMatch]: ...

    @abstractmethod
    def get_best_match(self, identity_id: str, max_score: float = 0.8) -> SearchMatch | None: ...


class AcousticProfileRepository(ABC):
    """Repositório para perfis acústicos."""
    @abstractmethod
    def get(self, version_id: str) -> AcousticProfile | None: ...

    @abstractmethod
    def add(self, profile: AcousticProfile) -> None: ...

    @abstractmethod
    def update(self, profile: AcousticProfile) -> None: ...

    @abstractmethod
    def delete(self, version_id: str) -> None: ...

    @abstractmethod
    def find_similar(self, profile: AcousticProfile, limit: int = 10) -> list[AcousticProfile]: ...


class RecommendationRepository(ABC):
    """Repositório para recomendações."""
    @abstractmethod
    def add(self, recommendation: Recommendation) -> None: ...

    @abstractmethod
    def get(self, recommendation_id: str) -> Recommendation | None: ...

    @abstractmethod
    def get_by_source(self, source_version_id: str, limit: int = 10) -> list[Recommendation]: ...

    @abstractmethod
    def get_by_identity(self, identity_id: str, limit: int = 20) -> list[Recommendation]: ...

    @abstractmethod
    def delete(self, recommendation_id: str) -> None: ...

    @abstractmethod
    def get_recent(self, limit: int = 50) -> list[Recommendation]: ...


class UserTasteProfileRepository(ABC):
    """Repositório para perfis de gosto do usuário."""
    @abstractmethod
    def get(self, user_id: str) -> UserTasteProfile | None: ...

    @abstractmethod
    def add(self, profile: UserTasteProfile) -> None: ...

    @abstractmethod
    def update(self, profile: UserTasteProfile) -> None: ...

    @abstractmethod
    def delete(self, user_id: str) -> None: ...

    @abstractmethod
    def list_all(self) -> list[UserTasteProfile]: ...


class AudioFeatureRepository(ABC):
    """Repositório para features de áudio."""
    @abstractmethod
    def get(self, version_id: str) -> AudioFeature | None: ...

    @abstractmethod
    def add(self, feature: AudioFeature) -> None: ...

    @abstractmethod
    def update(self, feature: AudioFeature) -> None: ...

    @abstractmethod
    def delete(self, version_id: str) -> None: ...

    @abstractmethod
    def find_similar(self, feature: AudioFeature, limit: int = 10) -> list[AudioFeature]: ...