from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

@dataclass
class PipelineConfig:
    """Configuração do pipeline com políticas de fallback."""
    timeout_seconds: float = 30.0
    max_retries: int = 3
    enable_fingerprint: bool = True
    enable_musicbrainz: bool = True
    enable_isrc: bool = True
    enable_identity_resolution: bool = True
    enable_materialization_link: bool = True
    enable_acoustic_analysis: bool = False
    enable_recommendation: bool = False
    user_prefs: Dict[str, Any] = field(default_factory=dict)
    fallback_policy: Dict[str, Any] = field(default_factory=dict)
    idempotency_key: Optional[str] = None