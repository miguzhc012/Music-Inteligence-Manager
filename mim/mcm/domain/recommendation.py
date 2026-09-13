from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


class RecommendationType(str, Enum):
    """Tipo de recomendação."""
    SIMILAR_ARTISTS = "similar_artists"
    SIMILAR_TRACKS = "similar_tracks"
    BASED_ON_HISTORY = "based_on_history"
    TRENDING = "trending"
    NEW_RELEASES = "new_releases"
    COLLECTIVE_TASTE = "collective_taste"  # Usuarios similares
    RADIO_STATION = "radio_station"
    CONTEXTUAL = "contextual"  # Hora do dia, clima, etc.


class SimilarityAlgorithm(str, Enum):
    """Algoritmo de similaridade."""
    COSINE_SIMILARITY = "cosine_similarity"
    JACCARD_INDEX = "jaccard_index"
    EUCLEIDEAN = "eucilean"
    COSINE_AUDIO = "cosine_audio_features"
    COLLABORATIVE_FILTERING = "collaborative_filtering"
    CONTENT_BASED = "content_based"


@dataclass(frozen=True)
class Recommendation:
    """Resultado de recomendação."""
    id: str = ""
    source_version_id: str | None = None
    target_identity_id: str | None = None
    target_version_id: str | None = None
    target_source_id: str | None = None
    type: RecommendationType = RecommendationType.SIMILAR_TRACKS
    algorithm: SimilarityAlgorithm = SimilarityAlgorithm.COSINE_SIMILARITY
    similarity_score: float = 0.0  # 0.0-1.0
    confidence: float = 0.0  # 0.0-1.0
    context: dict | None = None  # Dados contextuais (hora, dispositivo, etc.)
    created_at: str = ""
    
    def __post_init__(self):
        if not self.id:
            object.__setattr__(self, 'id', str(uuid4()))
        if not self.created_at:
            object.__setattr__(self, 'created_at', datetime.now().isoformat() + "Z")
    
    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.7
    
    @property
    def is_high_quality(self) -> bool:
        return self.similarity_score >= 0.8 and self.confidence >= 0.6


@dataclass(frozen=True)
class UserTasteProfile:
    """Perfil de gostos do usuário baseado em histórico."""
    user_id: str
    favorite_artists: list[str] = None
    favorite_genres: list[str] = None
    listening_count: int = 0
    total_ms_listened: int = 0
    skip_rate: float = 0.0
    repeat_rate: float = 0.0
    last_updated: str = ""
    
    def __post_init__(self):
        if self.favorite_artists is None:
            object.__setattr__(self, 'favorite_artists', [])
        if self.favorite_genres is None:
            object.__setattr__(self, 'favorite_genres', [])
        if not self.last_updated:
            object.__setattr__(self, 'last_updated', datetime.now().isoformat() + "Z")


@dataclass(frozen=True)
class AudioFeature:
    """Features de áudio para recomendação baseada em conteúdo."""
    version_id: str
    tempo_bpm: float | None = None
    key: str | None = None
    mode: str | None = None
    energy: float | None = None
    danceability: float | None = None
    valence: float | None = None
    acousticness: float | None = None
    instrumentalness: float | None = None
    liveness: float | None = None
    speechiness: float | None = None
    duration_ms: int | None = None
    analyzed_at: str | None = None