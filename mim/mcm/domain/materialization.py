from dataclasses import dataclass
from enum import Enum


class MaterializationState(str, Enum):
    UNAVAILABLE = "unavailable"
    CACHED = "cached"
    DOWNLOADED = "downloaded"


class MaterializationQuality(str, Enum):
    """Qualidade da materialização."""
    UNKNOWN = "unknown"
    LOW = "low"           # 128kbps or lower
    MEDIUM = "medium"     # 192-256kbps
    HIGH = "high"         # 320kbps
    LOSSLESS = "lossless" # FLAC, ALAC, WAV
    HIRES = "hires"       # > 44.1kHz/16bit


@dataclass(frozen=True)
class Materialization:
    """Estado físico/lógico de uma Source em um dispositivo."""
    source_id: str
    state: MaterializationState
    file_path: str | None = None           # Caminho do arquivo materializado
    device_id: str | None = None           # Dispositivo onde está armazenado
    quality: MaterializationQuality = MaterializationQuality.UNKNOWN
    format: str | None = None              # mp3, flac, m4a, etc.
    bitrate: int | None = None             # kbps
    sample_rate: int | None = None         # Hz
    bit_depth: int | None = None           # bits
    file_size: int | None = None           # bytes
    checksum: str | None = None            # SHA256 do arquivo
    created_at: str | None = None          # ISO 8601
    updated_at: str | None = None          # ISO 8601
    
    @property
    def is_available_locally(self) -> bool:
        return self.state in (MaterializationState.CACHED, MaterializationState.DOWNLOADED) and self.file_path is not None
    
    @property
    def is_permanent(self) -> bool:
        return self.state == MaterializationState.DOWNLOADED


@dataclass(frozen=True)
class DeviceStorage:
    """Informações de armazenamento de um dispositivo."""
    device_id: str
    total_bytes: int
    free_bytes: int
    path: str  # Mount point or root path
    
    @property
    def used_bytes(self) -> int:
        return self.total_bytes - self.free_bytes
    
    @property
    def usage_percent(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return (self.used_bytes / self.total_bytes) * 100