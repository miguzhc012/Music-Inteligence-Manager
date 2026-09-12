from dataclasses import dataclass

@dataclass(frozen=True)
class Identity:
    """Obra musical abstrata, independente de versão ou fonte."""
    id: str
    title: str
    artist: str
