from abc import ABC, abstractmethod

from .identity import Identity
from .version import Version
from .source import Source
from .library import LibraryEntry, FileStatus
from .release import Release, ReleaseTrack
from .resolution import Resolution
from .playback import QueueItem, PlaybackConfig, PlaybackState, PlaybackPosition


class IdentityRepository(ABC):
    @abstractmethod
    def get(self, identity_id: str) -> Identity: ...

    @abstractmethod
    def add(self, identity: Identity) -> None: ...


class VersionRepository(ABC):
    @abstractmethod
    def get(self, version_id: str) -> Version: ...

    @abstractmethod
    def add(self, version: Version) -> None: ...


class SourceRepository(ABC):
    @abstractmethod
    def get(self, source_id: str) -> Source: ...

    @abstractmethod
    def add(self, source: Source) -> None: ...


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