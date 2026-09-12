from typing import Optional, List
from uuid import uuid4

from mim.mcm.domain.resolution import Resolution, Evidence, EvidenceType
from mim.mcm.domain.ports import SourceResolver, ResolutionRepository, VersionRepository
from mim.mcm.domain.version import Version
from mim.mcm.domain.confidence import Confidence
from mim.mcm.domain.availability import Availability, AvailabilityStatus


class ResolutionService:
    """Serviço de aplicação para resolução de Version -> Source com confiança."""
    def __init__(self, version_repo: VersionRepository, resolution_repo: ResolutionRepository, source_resolver: SourceResolver):
        self.version_repo = version_repo
        self.resolution_repo = resolution_repo
        self.source_resolver = source_resolver

    def resolve_version(self, version_id: str, evidence_types: Optional[List[EvidenceType]] = None) -> Resolution:
        """Resolve uma Version para uma Source concreta usando evidências disponíveis.

        Args:
            version_id: ID da Version a resolver
            evidence_types: Tipos de evidência a considerar (None = todos)

        Returns:
            Resolution com evidências e confiança calculada.
        """
        # Busca ou cria resolução existente
        existing_resolution = self.resolution_repo.get_by_version(version_id)
        if existing_resolution:
            return existing_resolution

        # Busca Version
        version = self.version_repo.get(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")

        # Busca Identity para metadados adicionais
        identity = self.version_repo.get(version.identity_id)
        if identity:
            version.title = identity.title
            version.artist = identity.artist

        # Inicializa nova resolução
        resolution = Resolution(version_id=version_id)

        # Coleta evidências automaticamente com base em evidências configuradas
        automatic_evidence = self._collect_automatic_evidence(version, evidence_types)
        for evidence in automatic_evidence:
            resolution.add_evidence(evidence)

        # Tenta resolver via SourceResolver se evidências suficientes
        if resolution.confidence.value >= 0.5:
            resolved_source_id = self.source_resolver.resolve(version_id)
            if resolved_source_id:
                resolution.source_id = resolved_source_id
                resolution.resolved_at = datetime.now().isoformat() + "Z"

        # Salva resolução
        self.resolution_repo.add(resolution)
        return resolution

    def _collect_automatic_evidence(self, version: Version, allowed_types: Optional[List[EvidenceType]] = None) -> List[Evidence]:
        """Coleta evidências automáticas para uma Version.

        Implementação simplificada: adiciona evidência de metadados se disponível.
        """
        evidence = []
        if not allowed_types or EvidenceType.METADATA_MATCH in allowed_types:
            # Evidência de metadados (title, artist)
            if version.title:
                evidence.append(
                    Evidence(
                        type=EvidenceType.METADATA_MATCH,
                        weight=0.3,
                        description=f"Metadata match: {version.title}",
                    )
                )
        return evidence

    def get_resolution(self, resolution_id: str) -> Optional[Resolution]:
        """Obtém uma resolução existente."""
        return self.resolution_repo.get(resolution_id)

    def update_resolution(self, resolution_id: str, source_id: str, evidence: Evidence) -> Resolution:
        """Atualiza uma resolução com nova evidência ou source.
        """
        resolution = self.resolution_repo.get(resolution_id)
        if not resolution:
            raise ValueError(f"Resolution {resolution_id} not found")
        resolution.source_id = source_id
        resolution.add_evidence(evidence)
        self.resolution_repo.update(resolution)
        return resolution

    def list_resolutions_by_version(self, version_id: str) -> List[Resolution]:
        """Lista todas as resoluções para uma Version (histórico)."""
        # Implementação simples: busca todas as resoluções para esta versão
        # Em produção, adicionaria paginação e filtros
        all_resolutions = []
        # Busca a resolução atual
        current = self.resolution_repo.get_by_version(version_id)
        if current:
            all_resolutions.append(current)
        # Busca histórico de resoluções anteriores (se implementado)
        # Para agora, retornamos apenas a atual
        return all_resolutions