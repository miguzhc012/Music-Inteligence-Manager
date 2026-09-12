from dataclasses import dataclass
from enum import Enum

class MaterializationState(str, Enum):
    UNAVAILABLE = "unavailable"
    CACHED = "cached"
    DOWNLOADED = "downloaded"

@dataclass(frozen=True)
class Materialization:
    """Estado físico/lógico de uma Source em um dispositivo."""
    source_id: str
    state: MaterializationState
