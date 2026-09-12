from dataclasses import dataclass
from enum import Enum


class ReleaseType(str, Enum):
    """Tipo do lançamento: álbum, single, EP, compilação, etc."""
    ALBUM = "album"
    SINGLE = "single"
    EP = "ep"
    COMPILATION = "compilation"
    SOUNDTRACK = "soundtrack"
    LIVE = "live"
    REMIX = "remix"
    OTHER = "other"


@dataclass(frozen=True)
class Release:
    """
    Contexto de lançamento de uma obra.

    Uma Release agrupa Versions que foram lançadas juntas
    (ex.: faixas de um mesmo álbum, single com b-sides).
    """
    id: str
    identity_id: str
    title: str
    release_type: ReleaseType
    release_date: str  # ISO 8601 date string
    label: str | None = None
    catalog_number: str | None = None
    cover_url: str | None = None


@dataclass(frozen=True)
class ReleaseTrack:
    """
    Ocorrência de uma Version dentro de uma Release.

    Representa a relação Version/Release/Materialization.
    Permite rastrear posição, duração e metadados específicos da faixa no lançamento.
    """
    id: str
    release_id: str
    version_id: str
    track_number: int
    disc_number: int = 1
    duration_ms: int | None = None
    isrc: str | None = None
    explicit: bool = False