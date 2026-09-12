from dataclasses import dataclass
from enum import Enum

class AvailabilityStatus(str, Enum):
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    STALE = "stale"

@dataclass(frozen=True)
class Availability:
    """Disponibilidade independente de Confidence."""
    status: AvailabilityStatus
