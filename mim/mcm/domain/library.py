from dataclasses import dataclass
from enum import Enum


class FileStatus(str, Enum):
    PRESENT = "PRESENT"
    MISSING = "MISSING"


@dataclass(frozen=True)
class LibraryEntry:
    """Registro de um arquivo físico na Library.

    Representa apenas a presença do arquivo, sem identidade musical.
    """

    id: str
    path: str
    status: FileStatus
