from typing import Optional, List
from mim.mcm.domain.ports import SourceResolver
from mim.mcm.domain.source import Source, SourceType
from mim.mcm.domain.library import LibraryEntry, FileStatus
from mim.mcm.domain.ports import LibraryEntryRepository, SourceRepository


class LocalSourceResolver(SourceResolver):
    """Resolve Versions para Sources locais baseados na presença física na Library."""

    def __init__(self, library_repo: LibraryEntryRepository, source_repo: SourceRepository):
        self.library_repo = library_repo
        self.source_repo = source_repo

    def resolve(self, version_id: str) -> Optional[str]:
        """Tenta encontrar um source local para a versão, verificado pela Library."""
        sources = self.source_repo.get_by_version(version_id)
        local_sources = [s for s in sources if s.source_type == SourceType.LOCAL]

        for source in local_sources:
            # Aqui no futuro faremos match mais complexo. 
            # Por enquanto, se o source existe e é local, verificamos se há arquivo PRESENT.
            # O ID do source local muitas vezes mapeia para o ID do LibraryEntry ou vice-versa.
            # Simplificação: assume que source_id == library_entry_id para sources locais iniciais.
            entry = self.library_repo.get_by_id(source.id)
            if entry and entry.status == FileStatus.PRESENT:
                return source.id

        return None


class CacheSourceResolver(SourceResolver):
    """Placeholder para resolução em cache local."""
    def resolve(self, version_id: str) -> Optional[str]:
        return None


class RemoteSourceResolver(SourceResolver):
    """Placeholder para provedores remotos (Spotify, etc)."""
    def resolve(self, version_id: str) -> Optional[str]:
        return None


class DownloadSourceResolver(SourceResolver):
    """Placeholder para fontes de download permanente."""
    def resolve(self, version_id: str) -> Optional[str]:
        return None


class ResolverChain(SourceResolver):
    """Orquestra múltiplos resolvers em ordem de prioridade (custo zero primeiro)."""

    def __init__(self, resolvers: List[SourceResolver]):
        self.resolvers = resolvers

    def resolve(self, version_id: str) -> Optional[str]:
        for resolver in self.resolvers:
            source_id = resolver.resolve(version_id)
            if source_id:
                return source_id
        return None
