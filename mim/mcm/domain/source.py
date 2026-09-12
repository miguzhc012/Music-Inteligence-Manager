from dataclasses import dataclass
from enum import Enum

class SourceType(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"
    DOWNLOAD = "download"

@dataclass(frozen=True)
class Source:
    """Origem concreta que disponibiliza uma Version."""
    id: str
    version_id: str
    source_type: SourceType
