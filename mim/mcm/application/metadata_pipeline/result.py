from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from mim.mcm.domain.identity_resolution import IdentityResolutionResult
from mim.mcm.domain.audio_metadata import AudioMetadata

@dataclass
class PipelineResult:
    """Resultado do pipeline com metadados."""
    success: bool = False
    audio_metadata: Optional[AudioMetadata] = None
    identity_resolution: Optional[IdentityResolutionResult] = None
    version_selection: Optional[Dict] = None
    materialization_link: Optional[Dict] = None
    errors: List[Dict] = field(default_factory=list)
    stages: List[Dict] = field(default_factory=list)
    total_duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_audio(self) -> bool:
        return self.audio_metadata is not None

    @property
    def has_identity(self) -> bool:
        return self.identity_resolution is not None and self.identity_resolution.is_resolved

    @property
    def is_fully_successful(self) -> bool:
        return self.success and self.has_audio and self.has_identity