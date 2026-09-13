from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


class MatchQuality(str, Enum):
    EXACT = "exact"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class DiscoveryMethod(str, Enum):
    """Método de descoberta de música."""
    TITLE_MATCH = "title_match"
    ARTIST_MATCH = "artist_match"
    ALBUM_MATCH = "album_match"
    ISRC_MATCH = "isrc_match"
    ACOUSTIC_FINGERPRINT = "acoustic_fingerprint"
    FILE_HASH = "file_hash"
    MBID_MATCH = "mbid_match"
    USER_INPUT = "user_input"
    RECOMMENDATION = "recommendation"


@dataclass(frozen=True)
class SearchQuery:
    """Query genérica para busca de músicas."""
    query: str
    methods: list[DiscoveryMethod] | None = None
    filters: dict | None = None  # artist, album, year, etc.
    limit: int = 20
    
    def __post_init__(self):
        if self.methods is None:
            object.__setattr__(self, 'methods', [DiscoveryMethod.TITLE_MATCH])
        if self.filters is None:
            object.__setattr__(self, 'filters', {})


@dataclass(frozen=True)
class SearchMatch:
    """Resultado de uma busca."""
    identity_id: str
    title: str
    artist: str
    version_id: str | None = None
    source_id: str | None = None
    release_id: str | None = None
    album: str | None = None
    quality: MatchQuality = MatchQuality.NONE
    score: float = 0.0
    method: DiscoveryMethod = DiscoveryMethod.TITLE_MATCH
    metadata: dict | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    
    def __post_init__(self):
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})


@dataclass(frozen=True)
class AcousticProfile:
    """Perfil acústico de uma versão (para fingerprinting)."""
    version_id: str
    # Características extraídas do áudio
    tempo_bpm: float | None = None
    key: str | None = None  # Key of song (e.g., "C major")
    mode: str | None = None  # "major" or "minor"
    duration_ms: int | None = None
    energy: float | None = None  # 0.0-1.0
    danceability: float | None = None  # 0.0-1.0
    valence: float | None = None  # 0.0-1.0 (musical positiveness)
    audio_features: dict | None = None  # Raw features from analysis
    fingerprint_hash: str | None = None  # Unique fingerprint for matching