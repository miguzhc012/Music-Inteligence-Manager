from typing import List, Optional, Dict, Any, Callable
import asyncio
import time
import uuid

from dataclasses import dataclass
from enum import Enum

from mim.mcm.domain.identity_resolution import IdentityResolutionResult, ResolutionResultStatus
from mim.mcm.domain.audio_metadata import AudioMetadata, AudioCodec
from mim.mcm.domain.ports import (
    IdentityRepository,
    VersionRepository,
    MaterializationRepository,
)
from mim.mcm.domain.version import Version, VersionPolicy, VersionPolicyConfig


class VersionPolicyEngine:
    """Engine de políticas de versionamento com cadeia de fallback e preferências do usuário."""

    def __init__(self, config: Optional[VersionPolicyConfig] = None):
        self._config = config or VersionPolicyConfig()
        self._policies: List[VersionPolicy] = []
        self._build_policy_chain()

    def _build_policy_chain(self):
        """Constrói cadeia de políticas em ordem de prioridade."""
        self._policies = [
            VersionPolicy(
                name="acoustic",
                priority=1,
                condition=lambda m: m.acoustid_id is not None,
                score=0.95,
                description="Preferir versão com fingerprint acústico",
            ),
            VersionPolicy(
                name="tag_match",
                priority=2,
                condition=lambda m: m.title and m.artist,
                score=0.85,
                description="Preferir versão com match exato de título/artista",
            ),
            VersionPolicy(
                name="isrc_match",
                priority=3,
                condition=lambda m: m.isrc is not None,
                score=0.90,
                description="Preferir versão com ISRC exato",
            ),
            VersionPolicy(
                name="musicbrainz",
                priority=4,
                condition=lambda m: m.musicbrainz_track_id is not None,
                score=0.80,
                description="Preferir versão com MBID",
            ),
            VersionPolicy(
                name="default",
                priority=5,
                condition=lambda m: True,
                score=0.50,
                description="Versão padrão (mais recente)",
            ),
        ]

    def select_version(self, audio_metadata: AudioMetadata, candidate_versions: List[Version]) -> Optional[Version]:
        """Seleciona a melhor versão com base em políticas e preferências do usuário."""
        if not candidate_versions:
            return None

        # Aplicar preferências do usuário primeiro
        user_prefs = self._config.user_prefs or {}
        preferred_version_id = user_prefs.get("preferred_version_id")
        if preferred_version_id:
            for v in candidate_versions:
                if str(v.id) == preferred_version_id:
                    return v

        # Avaliar cada versão com as políticas
        scored_versions = []
        for version in candidate_versions:
            score = 0.0
            matched_policies = []
            for policy in self._policies:
                if policy.condition(audio_metadata):
                    policy_score = policy.score * policy.priority
                    score += policy_score
                    matched_policies.append(policy.name)
            if score == 0:
                score = 0.1  # Evitar zero total
            scored_versions.append((version, score, matched_policies))

        # Ordenar por score e prioridade
        scored_versions.sort(key=lambda x: (-x[1], x[0].priority if hasattr(x[0], 'priority') else 0))
        return scored_versions[0][0] if scored_versions else None

    def get_rationale(self, selected_version: Version, audio_metadata: AudioMetadata) -> str:
        """Gera rationale para a seleção de versão."""
        # Encontrar as políticas que corresponderam
        rationale_parts = []
        for policy in self._policies:
            if policy.condition(audio_metadata):
                rationale_parts.append(policy.description)
        base = f"Selecionado {selected_version.label or selected_version.id} via "
        if rationale_parts:
            base += ", ".join(rationale_parts[:3])
        else:
            base += "política padrão"
        return base

    def to_dict(self):
        return {
            "policies": [p.__dict__ for p in self._policies],
            "config": self._config.__dict__,
        }