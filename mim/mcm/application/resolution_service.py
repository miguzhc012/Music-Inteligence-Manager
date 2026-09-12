from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from mim.mcm.domain.resolution import Resolution, Evidence, EvidenceType
from mim.mcm.domain.ports import (
    SourceResolver, 
    ResolutionRepository, 
    VersionRepository,
    SourceRepository,
)
from mim.mcm.domain.version import Version
from mim.mcm.domain.confidence import Confidence
from mim.mcm.domain.availability import Availability, AvailabilityStatus
from mim.mcm.domain.source import Source, SourceType
from mim.mcm.domain.library import LibraryEntry, FileStatus
from mim.mcm.domain.ports import LibraryEntryRepository


@dataclass
class ResolutionConfig:
    """Configuração de pesos para evidence types."""
    weights: dict[EvidenceType, float] = field(default_factory=lambda: {
        EvidenceType.FILE_HASH: 0.9,
        EvidenceType.ACOUSTIC_FINGERPRINT: 0.8,
        EvidenceType.ISRC_MATCH: 0.7,
        EvidenceType.MBID_MATCH: 0.7,
        EvidenceType.METADATA_MATCH: 0.3,
        EvidenceType.PROVIDER_ASSERTION: 0.5,
        EvidenceType.USER_CONFIRMATION: 1.0,
    })
    confidence_threshold: float = 0.7


class LocalAvailabilityChecker:
    """Verifica disponibilidade real de sources locais."""

    def __init__(self, library_repo: LibraryEntryRepository):
        self.library_repo = library_repo

    def check(self, source: Source) -> AvailabilityStatus:
        if source.source_type != SourceType.LOCAL:
            return AvailabilityStatus.UNKNOWN
        
        entry = self.library_repo.get_by_id(source.id)
        if entry and entry.status == FileStatus.PRESENT:
            return AvailabilityStatus.AVAILABLE
        return AvailabilityStatus.UNAVAILABLE


class ResolutionService:
    """Serviço de aplicação para resolução de Version -> Source com confiança."""

    def __init__(
        self,
        version_repo: VersionRepository,
        source_repo: SourceRepository,
        resolution_repo: ResolutionRepository,
        source_resolver: SourceResolver,
        library_repo: LibraryEntryRepository,
        config: Optional[ResolutionConfig] = None,
    ):
        self.version_repo = version_repo
        self.source_repo = source_repo
        self.resolution_repo = resolution_repo
        self.source_resolver = source_resolver
        self.library_repo = library_repo
        self.config = config or ResolutionConfig()
        self.availability_checker = LocalAvailabilityChecker(library_repo)

    def resolve_version(self, version_id: str, evidence_types: Optional[List[EvidenceType]] = None) -> Resolution:
        """Resolve uma Version para uma Source concreta usando evidências disponíveis."""
        # Busca ou cria resolução existente
        existing_resolution = self.resolution_repo.get_by_version(version_id)
        if existing_resolution:
            return existing_resolution

        # Busca Version
        version = self.version_repo.get(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")

        # Inicializa nova resolução
        resolution = Resolution(version_id=version_id)

        # Coleta evidências automáticas
        automatic_evidence = self._collect_automatic_evidence(version, evidence_types)
        for evidence in automatic_evidence:
            resolution.add_evidence(evidence)

        # Tenta resolver via SourceResolver se confiança suficiente
        if resolution.confidence.value >= 0.3:
            resolved_source_id = self.source_resolver.resolve(version_id)
            if resolved_source_id:
                resolution.source_id = resolved_source_id
                source = self.source_repo.get(resolved_source_id)
                if source:
                    availability_status = self.availability_checker.check(source)
                    resolution.availability = Availability(availability_status)
                resolution.resolved_at = datetime.now().isoformat() + "Z"

        # Salva resolução
        self.resolution_repo.add(resolution)
        return resolution

    def _collect_automatic_evidence(
        self, 
        version: Version, 
        allowed_types: Optional[List[EvidenceType]] = None
    ) -> List[Evidence]:
        """Coleta evidências automáticas para uma Version."""
        evidence = []

        # 1. METADATA_MATCH - se tem title/artist na version
        if not allowed_types or EvidenceType.METADATA_MATCH in allowed_types:
            if version.label:
                weight = self.config.weights.get(EvidenceType.METADATA_MATCH, 0.3)
                evidence.append(
                    Evidence(
                        type=EvidenceType.METADATA_MATCH,
                        weight=weight,
                        description=f"Metadata match: {version.label}",
                    )
                )

        # 2. Check if local source exists and has file
        local_sources = self.source_repo.get_by_version(version.id)
        local_sources = [s for s in local_sources if s.source_type == SourceType.LOCAL]
        
        for source in local_sources:
            entry = self.library_repo.get_by_id(source.id)
            if entry and entry.status == FileStatus.PRESENT:
                # FILE_HASH evidence - highest weight
                if not allowed_types or EvidenceType.FILE_HASH in allowed_types:
                    weight = self.config.weights.get(EvidenceType.FILE_HASH, 0.9)
                    evidence.append(
                        Evidence(
                            type=EvidenceType.FILE_HASH,
                            weight=weight,
                            description=f"Local file present: {entry.path}",
                            source_id=source.id,
                        )
                    )

        return evidence

    def get_resolution(self, resolution_id: str) -> Optional[Resolution]:
        """Obtém uma resolução existente."""
        return self.resolution_repo.get(resolution_id)

    def update_resolution(self, resolution_id: str, source_id: str, evidence: Evidence) -> Resolution:
        """Atualiza uma resolução com nova evidência ou source."""
        resolution = self.resolution_repo.get(resolution_id)
        if not resolution:
            raise ValueError(f"Resolution {resolution_id} not found")
        resolution.source_id = source_id
        resolution.add_evidence(evidence)
        self.resolution_repo.update(resolution)
        return resolution

    def list_resolutions_by_version(self, version_id: str) -> List[Resolution]:
        """Lista todas as resoluções para uma Version (histórico)."""
        current = self.resolution_repo.get_by_version(version_id)
        return [current] if current else []