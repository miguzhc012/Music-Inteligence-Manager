from dataclasses import dataclass

@dataclass(frozen=True)
class Version:
    """Variação específica de uma Identity (ex.: normal, acoustic, live)."""
    id: str
    identity_id: str
    label: str
