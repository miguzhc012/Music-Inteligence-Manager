from dataclasses import dataclass
from enum import Enum

class SessionState(str, Enum):
    ACTIVE = "active"
    WAITING_FOR_ROUTE = "waiting_for_route"
    PLAYBACK_UNAVAILABLE = "playback_unavailable"

@dataclass(frozen=True)
class Session:
    """Sessão de reprodução, controlada pelo MCL. Contém apenas referências por ID."""
    id: str
    source_id: str
    device_id: str
    state: SessionState = SessionState.ACTIVE
