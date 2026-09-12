from dataclasses import dataclass, field
from typing import Set

@dataclass(frozen=True)
class Device:
    """Dispositivo cujo comportamento é determinado por capabilities."""
    id: str
    type: str
    capabilities: Set[str] = field(default_factory=set)
