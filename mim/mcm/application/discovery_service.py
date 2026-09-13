from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from mim.mcm.domain.discovery import SearchQuery, SearchMatch, DiscoveryMethod, MatchQuality, AcousticProfile
from mim.mcm.domain.ports import DiscoveryRepository, AcousticProfileRepository, VersionRepository, IdentityRepository
from mim.mcm.domain.version import Version
from mim.mcm.domain.identity import Identity


@dataclass
class DiscoveryService:
    """Serviço de descoberta de músicas."""
    
    discovery_repo: DiscoveryRepository
    version_repo: VersionRepository
    identity_repo: IdentityRepository
    
    def search(self, query: SearchQuery) -> List[SearchMatch]:
        """Busca músicas baseada na query."""
        results = []
        
        # Tenta matches por título (mais comum)
        if DiscoveryMethod.TITLE_MATCH in query.methods:
            matches = self._search_by_title(query.query)
            results.extend(matches)
        
        # Tenta matches por artista
        if DiscoveryMethod.ARTIST_MATCH in query.methods:
            matches = self._search_by_artist(query.query)
            results.extend(matches)
        
        # Remove duplicados e ordena por score
        seen = set()
        unique_results = []
        for match in results:
            if match.id not in seen:
                seen.add(match.id)
                unique_results.append(match)
        
        unique_results.sort(key=lambda m: m.score, reverse=True)
        return unique_results[:query.limit]
    
    def _search_by_title(self, query_str: str) -> List[SearchMatch]:
        """Busca matches por título (simplificado - em produção usaria full-text search)."""
        # Placeholder: retornar matches baseados em identidade
        # Em produção, implementaria fuzzy matching ou texto completo
        return []
    
    def _search_by_artist(self, query_str: str) -> List[SearchMatch]:
        """Busca matches por artista."""
        return []
    
    def find_similar(self, version_id: str, limit: int = 10) -> List[SearchMatch]:
        """Encontra músicas similares baseada em acústica."""
        # TODO: Implementar baseado em acoustic fingerprint
        return []
    
    def get_best_match(self, identity_id: str, max_score: float = 0.8) -> Optional[SearchMatch]:
        """Retorna o melhor match para uma identidade."""
        return self.discovery_repo.get_best_match(identity_id, max_score)
    
    def save_match(self, match: SearchMatch) -> None:
        """Salva um match de descoberta."""
        self.discovery_repo.save_match(match)


class AcousticAnalysisService:
    """Serviço para análise acústica de arquivos de áudio."""
    
    def __init__(self, acoustic_repo: AcousticProfileRepository):
        self.acoustic_repo = acoustic_repo
    
    def analyze(self, version_id: str, file_path: str) -> AcousticProfile:
        """Análisa arquivo de áudio e retorna perfil acústico."""
        # Placeholder - em produção usaria librosa ou similar
        profile = AcousticProfile(
            version_id=version_id,
            tempo_bpm=120.0,
            key="C",
            mode="major",
            duration_ms=180000,
            energy=0.8,
            danceability=0.7,
            valence=0.9,
        )
        self.acoustic_repo.add(profile)
        return profile
    
    def get_profile(self, version_id: str) -> Optional[AcousticProfile]:
        """Obtém perfil acústico de uma versão."""
        return self.acoustic_repo.get(version_id)
    
    def find_similar(self, version_id: str, limit: int = 10) -> List[AcousticProfile]:
        """Encontra perfis acústicos similares."""
        profile = self.acoustic_repo.get(version_id)
        if not profile:
            return []
        return self.acoustic_repo.find_similar(profile, limit)