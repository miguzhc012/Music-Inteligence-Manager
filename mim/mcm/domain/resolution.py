from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import uuid4

from .confidence import Confidence
from .availability import Availability, AvailabilityStatus


class EvidenceType(str, Enum):
    """Tipos de evidência para resolução."""
    METADATA_MATCH = "metadata_match"       # Match por metadados (title, artist, album)
    ACOUSTIC_FINGERPRINT = "acoustic_fingerprint"  # Match por fingerprint acústico
    ISRC_MATCH = "isrc_match"               # Match por ISRC
    MBID_MATCH = "mbid_match"               # Match por MusicBrainz ID
    FILE_HASH = "file_hash"                 # Match por hash do arquivo
    USER_CONFIRMATION = "user_confirmation" # Confirmação manual do usuário
    PROVIDER_ASSERTION = "provider_assertion"  # Assertiva do provider (ex.: Spotify API)


@dataclass(frozen=True)
class Evidence:
    """
    Evidência individual que suporta uma resolução.

    Cada evidência tem um tipo, peso e descrição.
    """
    type: EvidenceType
    weight: float  # 0.0 a 1.0
    description: str
    source_id: str | None = None  # ID da Source relacionada, se aplicável


@dataclass
class Resolution:
    """
    Resultado da resolução de uma Version para uma Source concreta.

    A resolução agrega múltiplas evidências e calcula um Confidence score.
    Permite rastrear COMO e POR QUE uma fonte foi escolhida.
    """
    version_id: str
    source_id: str | None = None
    confidence: Confidence = field(default_factory=lambda: Confidence(0.0))
    availability: Availability = field(default_factory=lambda: Availability(AvailabilityStatus.UNKNOWN))
    evidence: list[Evidence] = field(default_factory=list)
    resolved_at: str | None = None  # ISO 8601 timestamp
    resolution_id: str = field(default_factory=lambda: str(uuid4()))

    def add_evidence(self, evidence: Evidence) -> None:
        """Adiciona evidência e recalcula confiança."""
        self.evidence.append(evidence)
        self._recalculate_confidence()

    def _recalculate_confidence(self) -> None:
        """Recalcula confiança baseada na soma ponderada das evidências."""
        if not self.evidence:
            self.confidence = Confidence(0.0)
            return

        total_weight = sum(e.weight for e in self.evidence)
        # Normaliza para 0.0-1.0
        self.confidence = Confidence(min(total_weight, 1.0))

    def is_resolved(self) -> bool:
        """Verifica se a resolução tem source e confiança suficiente."""
        return (
            self.source_id is not None
            and self.confidence.value >= 0.7
            and self.availability.status == AvailabilityStatus.AVAILABLE
        )

    def get_best_source_id(self) -> str | None:
        """Retorna o source_id se resolvido, None caso contrário."""
        return self.source_id if self.is_resolved() else None