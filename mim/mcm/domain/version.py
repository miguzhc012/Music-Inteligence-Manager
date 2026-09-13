from dataclasses import dataclass, field
from typing import Optional, Callable
from mim.mcm.domain.audio_metadata import AudioMetadata


@dataclass(frozen=True)
class Version:
    """Variação específica de uma Identity (ex.: normal, acoustic, live)."""
    id: str
    identity_id: str
    label: str


@dataclass(frozen=True)
class VersionPolicy:
    """Política individual de seleção de versão com pontuação."""
    name: str
    priority: int
    condition: Callable[[AudioMetadata], bool]
    score: float
    description: str


@dataclass(frozen=True)
class VersionPolicyConfig:
    """Configuração para o motor de políticas de versionamento."""
    hash_threshold: float = 1.0
    isrc_weight: float = 0.95
    mbid_weight: float = 0.9
    tags_weight: float = 0.4
    fingerprint_weight: float = 0.8
    confidence_threshold: float = 0.7
    allow_conflicts: bool = False
    user_prefs: dict = field(default_factory=dict)
    fallback_policy: dict = field(default_factory=dict)


__all__ = ["Version", "VersionPolicy", "VersionPolicyConfig"]