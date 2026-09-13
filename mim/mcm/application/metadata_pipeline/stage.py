from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any
from enum import Enum

class PipelineStep(str, Enum):
    """Ordem das etapas do pipeline."""
    AUDIO_EXTRACTION = "audio_extraction"
    TAG_NORMALIZATION = "tag_normalization"
    ARTWORK_EXTRACTION = "artwork_extraction"
    FINGERPRINT_GENERATION = "fingerprint_generation"
    MUSICBRAINZ_ENRICHMENT = "musicbrainz_enrichment"
    ISRC_VALIDATION = "isrc_validation"
    IDENTITY_RESOLUTION = "identity_resolution"
    MATERIALIZATION_LINK = "materialization_link"
    ACOUSTIC_ANALYSIS = "acoustic_analysis"
    RECOMMENDATION_GENERATION = "recommendation_generation"

@dataclass
class PipelineStage:
    """Definição de uma etapa do pipeline."""
    step: PipelineStep
    handler: Callable
    required: bool = True
    timeout: Optional[float] = None
    retry_policy: Optional[Dict] = None
    metrics: Dict[str, Any] = field(default_factory=dict)