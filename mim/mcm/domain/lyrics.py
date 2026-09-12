from dataclasses import dataclass
from enum import Enum


class LyricsType(str, Enum):
    """Tipo de letra."""
    SYNCED = "synced"      # Letras sincronizadas (LRC)
    UNSYNCED = "unsynced"  # Letras simples (texto)


class LyricsSource(str, Enum):
    """Fonte da letra."""
    LOCAL = "local"           # Arquivo .lrc ou .txt junto ao áudio
    EMBEDDED = "embedded"     # Dentro do arquivo de áudio (ID3, Vorbis)
    PROVIDER = "provider"     # API externa (LRCLIB, Genius, etc.)
    USER = "user"             # Editada manualmente pelo usuário


@dataclass(frozen=True)
class LyricsLine:
    """Linha individual de letra sincronizada."""
    timestamp_ms: int
    text: str
    translation: str | None = None  # Tradução opcional


@dataclass(frozen=True)
class Lyrics:
    """Letra de uma versão."""
    version_id: str
    lyrics_type: LyricsType
    source: LyricsSource
    content: str  # Texto completo (unsynced) ou vazio se só synced
    lines: list[LyricsLine] = None  # Linhas sincronizadas
    language: str | None = None
    fetched_at: str | None = None  # ISO 8601
    
    def __post_init__(self):
        if self.lines is None:
            object.__setattr__(self, 'lines', [])
    
    @property
    def is_synced(self) -> bool:
        return self.lyrics_type == LyricsType.SYNCED and len(self.lines) > 0
    
    def get_line_at(self, position_ms: int) -> LyricsLine | None:
        """Retorna a linha ativa na posição dada (para letras sincronizadas)."""
        if not self.is_synced:
            return None
        
        active_line = None
        for line in self.lines:
            if line.timestamp_ms <= position_ms:
                active_line = line
            else:
                break
        return active_line
    
    def get_next_line(self, position_ms: int) -> LyricsLine | None:
        """Retorna a próxima linha após a posição."""
        if not self.is_synced:
            return None
        
        for line in self.lines:
            if line.timestamp_ms > position_ms:
                return line
        return None


@dataclass(frozen=True)
class LyricsSearchQuery:
    """Query para busca de letras."""
    title: str
    artist: str
    album: str | None = None
    duration_ms: int | None = None
    isrc: str | None = None