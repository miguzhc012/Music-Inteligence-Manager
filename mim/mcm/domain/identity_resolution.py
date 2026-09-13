"""
Fase 3 - Domain: IdentityResolution
Resolve identidade musical a partir de múltiplas fontes de evidência.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import uuid4


class ResolutionStrategy(str, Enum):
    EXACT_HASH = "exact_hash"
    ISRC_MATCH = "isrc_match"
    MUSICBRAINZ_MBD = "musicbrainz_mbd"
    TAGS_MATCH = "tags_match"
    FINGERPRINT = "fingerprint"
    MANUAL = "manual"


class ResolutionResultStatus(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    CONFLICT = "conflict"
    MANUAL_REQUIRED = "manual_required"


@dataclass(frozen=True)
class ResolutionEvidence:
    """Evidência individual para resolução."""
    strategy: ResolutionStrategy
    weight: float  # 0.0-1.0
    score: float  # 0.0-1.0
    description: str
    source_data: dict = field(default_factory=dict)
    confidence: float = 0.0

    @property
    def adjusted_score(self) -> float:
        return self.weight * self.score


@dataclass(frozen=True)
class IdentityResolutionResult:
    """Resultado da resolução de identidade."""
    status: ResolutionResultStatus
    evidence: list[ResolutionEvidence]
    resolved_identity_id: Optional[str] = None
    resolved_version_id: Optional[str] = None
    confidence: float = 0.0
    rationale: str = ""
    manual_review_required: bool = False
    conflict_details: Optional[str] = None

    @property
    def is_resolved(self) -> bool:
        return self.status == ResolutionResultStatus.RESOLVED and self.confidence >= 0.7

    @property
    def requires_manual_review(self) -> bool:
        return self.status == ResolutionResultStatus.MANUAL_REQUIRED


@dataclass(frozen=True)
class IdentityResolutionConfig:
    """Configuração do resolution engine."""
    hash_threshold: float = 1.0
    isrc_weight: float = 0.95
    mbid_weight: float = 0.9
    tags_weight: float = 0.4
    fingerprint_weight: float = 0.8
    confidence_threshold: float = 0.7
    allow_conflicts: bool = False