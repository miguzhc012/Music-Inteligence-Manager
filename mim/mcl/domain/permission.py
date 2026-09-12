from dataclasses import dataclass
from enum import Enum

class SubjectType(str, Enum):
    DEVICE = "device"
    USER = "user"
    MIA = "mia"

@dataclass(frozen=True)
class Subject:
    """Quem solicita permissão (dispositivo, usuário, MIA)."""
    id: str
    type: SubjectType

@dataclass(frozen=True)
class Permission:
    """Permissão concedida a um Subject sobre um recurso e ação."""
    subject_id: str
    action: str
    resource: str
