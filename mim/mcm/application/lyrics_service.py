from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from mim.mcm.domain.lyrics import Lyrics, LyricsLine, LyricsType, LyricsSource, LyricsSearchQuery
from mim.mcm.domain.ports import LyricsRepository, LyricsProvider, VersionRepository, IdentityRepository
from mim.mcm.domain.version import Version
from mim.mcm.domain.identity import Identity


class LocalLyricsProvider(LyricsProvider):
    """Provedor de letras locais (arquivos .lrc/.txt na mesma pasta do áudio)."""
    
    def __init__(self, library_repo):
        self.library_repo = library_repo
    
    def search(self, query: LyricsSearchQuery) -> List[Lyrics]:
        # Placeholder: buscar arquivo .lrc/.txt na mesma pasta
        return []
    
    def fetch_by_id(self, provider_id: str) -> Optional[Lyrics]:
        return None


class EmbeddedLyricsProvider(LyricsProvider):
    """Provedor de letras embutidas no arquivo de áudio (ID3 SYLT, Vorbis COMMENT, etc.)."""
    
    def __init__(self, library_repo, source_repo):
        self.library_repo = library_repo
        self.source_repo = source_repo
    
    def search(self, query: LyricsSearchQuery) -> List[Lyrics]:
        return []
    
    def fetch_by_id(self, provider_id: str) -> Optional[Lyrics]:
        return None


class RemoteLyricsProvider(LyricsProvider):
    """Provedor remoto de letras (LRCLIB, Genius, etc.) - stub."""
    
    def search(self, query: LyricsSearchQuery) -> List[Lyrics]:
        # TODO: implementar chamadas HTTP para LRCLIB API
        return []
    
    def fetch_by_id(self, provider_id: str) -> Optional[Lyrics]:
        return None


@dataclass
class LyricsService:
    """Serviço de aplicação para gerenciar letras."""
    
    lyrics_repo: LyricsRepository
    providers: List[LyricsProvider]
    version_repo: VersionRepository
    identity_repo: IdentityRepository
    
    def get_lyrics(self, version_id: str) -> Optional[Lyrics]:
        """Obtém letras para uma versão (cache local primeiro)."""
        # 1. Tenta cache local
        lyrics = self.lyrics_repo.get(version_id)
        if lyrics:
            return lyrics
        
        # 2. Tenta provedores em ordem de prioridade
        version = self.version_repo.get(version_id)
        if not version:
            return None
        
        identity = self.identity_repo.get(version.identity_id)
        if not identity:
            return None
        
        query = LyricsSearchQuery(
            title=identity.title,
            artist=identity.artist,
        )
        
        for provider in self.providers:
            try:
                results = provider.search(query)
                if results:
                    # Pega o primeiro resultado
                    lyrics = results[0]
                    lyrics.version_id = version_id
                    self.lyrics_repo.add(lyrics)
                    return lyrics
            except Exception:
                continue
        
        return None
    
    def save_lyrics(self, version_id: str, lyrics: Lyrics) -> Lyrics:
        """Salva letras (manual ou corrigidas pelo usuário)."""
        lyrics = Lyrics(
            version_id=version_id,
            lyrics_type=lyrics.lyrics_type,
            source=LyricsSource.USER,
            content=lyrics.content,
            lines=lyrics.lines,
            language=lyrics.language,
            fetched_at=datetime.now().isoformat() + "Z",
        )
        self.lyrics_repo.add(lyrics)
        return lyrics
    
    def delete_lyrics(self, version_id: str) -> None:
        """Remove letras de uma versão."""
        self.lyrics_repo.delete(version_id)
    
    def get_current_line(self, version_id: str, position_ms: int) -> Optional[LyricsLine]:
        """Obtém a linha ativa na posição atual."""
        lyrics = self.lyrics_repo.get(version_id)
        if not lyrics:
            return None
        return lyrics.get_line_at(position_ms)
    
    def get_next_line(self, version_id: str, position_ms: int) -> Optional[LyricsLine]:
        """Obtém a próxima linha."""
        lyrics = self.lyrics_repo.get(version_id)
        if not lyrics:
            return None
        return lyrics.get_next_line(position_ms)