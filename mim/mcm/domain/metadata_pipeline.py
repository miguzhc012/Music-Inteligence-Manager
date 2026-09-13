"""
MetadataExtractionPipeline - Orchestrates audio extraction, tag normalization,
artwork extraction, fingerprint generation, and MusicBrainz enrichment.
"""
import asyncio
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum, auto

from mim.mcm.domain.audio_metadata import AudioExtractionService, AudioMetadata
from mim.mcm.application.identity_resolution import IdentityResolutionService
from mim.mcm.application.audio_extraction import AudioExtractionApplicationService
from mim.mcm.application.identity_resolution import IdentityResolutionApplicationService
from mim.mcm.application.discovery_service import DiscoveryService, AcousticAnalysisService
from mim.mcm.application.recommendation_service import RecommendationService
from mim.mcm.domain.ports import (
    SourceRepository,
    IdentityRepository,
    VersionRepository,
    MaterializationRepository,
    DiscoveryRepository,
    AcousticProfileRepository,
)


class PipelineStep(str, Enum):
    AUDIO_EXTRACTION = "audio_extraction"
    TAG_NORMALIZATION = "tag_normalization"
    ARTWORK_EXTRACTION = "artwork_extraction"
    FINGERPRINT_GENERATION = "fingerprint_generation"
    MUSICBRAINZ_ENRICHMENT = "musicbrainz_enrichment"
    IDENTITY_RESOLUTION = "identity_resolution"


@dataclass
class PipelineResult:
    """Result of a pipeline step."""
    step: PipelineStep
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    """Configuration for the metadata extraction pipeline."""
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_delay: float = 0.5
    enable_fingerprint: bool = True
    enable_musicbrainz: bool = True
    enable_identity_resolution: bool = True
    confidence_threshold: float = 0.7


@dataclass
class PipelineResultSet:
    """Complete result of running the pipeline."""
    success: bool
    audio_metadata: Optional[AudioMetadata] = None
    identity_resolution: Optional[Any] = None  # IdentityResolutionResult
    acoustic_profile: Optional[Any] = None  # AcousticProfile
    steps: List[PipelineResult] = field(default_factory=list)
    total_duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)

    @property
    def has_audio(self) -> bool:
        return self.audio_metadata is not None

    @property
    def has_identity(self) -> bool:
        return self.identity_resolution is not None and self.identity_resolution.is_resolved

    @property
    def is_fully_successful(self) -> bool:
        return self.success and len(self.errors) == 0


class MetadataExtractionPipeline:
    """
    Orchestrates metadata extraction with pluggable stages.
    Each stage can fail independently without stopping the pipeline.
    """

    def __init__(
        self,
        audio_extraction_service: AudioExtractionApplicationService,
        identity_resolution_service: IdentityResolutionApplicationService,
        discovery_service: DiscoveryService,
        acoustic_analysis_service: AcousticAnalysisService,
        recommendation_service: RecommendationService,
        source_repo: SourceRepository,
        identity_repo: IdentityRepository,
        version_repo: VersionRepository,
        materialization_repo,
        discovery_repo,
        acoustic_profile_repo,
        config: Optional[PipelineConfig] = None,
    ):
        self._audio_service = audio_extraction_service
        self._identity_service = identity_resolution_service
        self._discovery_service = discovery_service
        self._acoustic_service = acoustic_analysis_service
        self._recommendation_service = recommendation_service
        self._source_repo = source_repo
        self._identity_repo = identity_repo
        self._version_repo = version_repo
        self._materialization_repo = materialization_repo
        self._discovery_repo = discovery_repo
        self._acoustic_profile_repo = acoustic_profile_repo
        self._config = config or PipelineConfig()

    async def run(self, file_path: str) -> PipelineResultSet:
        """Run the full metadata extraction pipeline."""
        start_time = time.time()
        result_set = PipelineResultSet(success=False)

        # Stage 1: Audio Extraction (always required)
        audio_result = await self._run_with_timeout_and_retry(
            PipelineStep.AUDIO_EXTRACTION,
            self._extract_audio,
            file_path,
        )
        result_set.steps.append(audio_result)
        if audio_result.success:
            result_set.audio_metadata = audio_result.data
        else:
            result_set.errors.append(f"Audio extraction failed: {audio_result.error}")
            # Continue anyway - we might still have partial data

        # Stage 2: Tag Normalization (always runs if we have audio)
        if audio_result.success:
            tag_result = await self._run_with_timeout_and_retry(
                PipelineStep.TAG_NORMALIZATION,
                self._normalize_tags,
                audio_result.data,
            )
            result_set.steps.append(tag_result)
            if tag_result.success:
                # Update audio metadata with normalized tags
                if result_set.audio_metadata:
                    # In production, would update the object
                    pass
            else:
                result_set.errors.append(f"Tag normalization failed: {tag_result.error}")

        # Stage 3: Artwork Extraction
        if audio_result.success:
            artwork_result = await self._run_with_timeout_and_retry(
                PipelineStep.ARTWORK_EXTRACTION,
                self._extract_artwork,
                audio_result.data,
            )
            result_set.steps.append(artwork_result)
            if artwork_result.success:
                # Attach artwork to audio metadata
                if result_set.audio_metadata:
                    # In production, would update the object
                    pass
            else:
                result_set.errors.append(f"Artwork extraction failed: {artwork_result.error}")

        # Stage 4: Fingerprint Generation (optional)
        if self._config.enable_fingerprint and audio_result.success:
            fingerprint_result = await self._run_with_timeout_and_retry(
                PipelineStep.FINGERPRINT_GENERATION,
                self._generate_fingerprint,
                audio_result.data,
            )
            result_set.steps.append(fingerprint_result)
            if fingerprint_result.success:
                # Store fingerprint for later use
                pass
            else:
                result_set.errors.append(f"Fingerprint generation failed: {fingerprint_result.error}")

        # Stage 5: MusicBrainz Enrichment (optional)
        if self._config.enable_musicbrainz and audio_result.success:
            mb_result = await self._run_with_timeout_and_retry(
                PipelineStep.MUSICBRAINZ_ENRICHMENT,
                self._enrich_with_musicbrainz,
                audio_result.data,
            )
            result_set.steps.append(mb_result)
            if mb_result.success:
                # Enrich audio metadata with MBID data
                pass
            else:
                result_set.errors.append(f"MusicBrainz enrichment failed: {mb_result.error}")

        # Stage 6: Identity Resolution (optional)
        if self._config.enable_identity_resolution and audio_result.success:
            id_result = await self._run_with_timeout_and_retry(
                PipelineStep.IDENTITY_RESOLUTION,
                self._resolve_identity,
                audio_result.data,
            )
            result_set.steps.append(id_result)
            if id_result.success:
                result_set.identity_resolution = id_result.data
            else:
                result_set.errors.append(f"Identity resolution failed: {id_result.error}")

        # Finalize
        result_set.total_duration_ms = (time.time() - start_time) * 1000
        result_set.success = len(result_set.errors) == 0 and result_set.audio_metadata is not None

        return result_set

    async def _run_with_timeout_and_retry(
        self,
        step: PipelineStep,
        func,
        *args,
    ) -> PipelineResult:
        """Run a function with timeout and retry logic."""
        last_error = None
        for attempt in range(self._config.max_retries + 1):
            try:
                # Wrap in asyncio.wait_for for timeout
                result = await asyncio.wait_for(
                    asyncio.to_thread(func, *args),
                    timeout=self._config.timeout_seconds,
                )
                return PipelineResult(
                    step=step,
                    success=True,
                    data=result if isinstance(result, dict) else {"result": result},
                    duration_ms=0.0,  # Would measure actual time in production
                )
            except asyncio.TimeoutError:
                last_error = f"Timeout after {self._config.timeout_seconds}s"
            except Exception as e:
                last_error = str(e)
            
            if attempt < self._config.max_retries:
                await asyncio.sleep(self._config.retry_delay)

        return PipelineResult(
            step=step,
            success=False,
            error=last_error,
            duration_ms=0.0,
        )

    # --- Pipeline Stage Implementations ---

    def _extract_audio(self, file_path: str) -> AudioMetadata:
        """Extract audio metadata using mutagen."""
        return self._audio_service.extract(file_path)

    def _normalize_tags(self, audio_data: AudioMetadata) -> Dict[str, Any]:
        """Normalize and clean tags (placeholder)."""
        # In production, would:
        # - Convert encoding to UTF-8
        # - Remove invalid characters
        # - Standardize genre names
        # - Fix common tagging errors
        return {"normalized": True, "original": audio_data.__dict__}

    def _extract_artwork(self, audio_data: AudioMetadata) -> Dict[str, Any]:
        """Extract and save artwork (placeholder)."""
        # In production, would:
        # - Extract embedded artwork
        # - Save to cache/disk
        # - Generate thumbnails
        # - Return artwork info/path
        return {"extracted": True, "artwork_present": bool(audio_data.artwork)}

    def _generate_fingerprint(self, audio_data: AudioMetadata) -> Dict[str, Any]:
        """Generate acoustic fingerprint (placeholder)."""
        # In production, would use Chromaprint/AcoustID
        return {"fingerprint_generated": True, "method": "placeholder"}

    def _enrich_with_musicbrainz(self, audio_data: AudioMetadata) -> Dict[str, Any]:
        """Enrich with MusicBrainz data (placeholder)."""
        # In production, would:
        # - Query MusicBrainz API by track/artist/album
        # - Get MBIDs, release info, etc.
        # - Update audio_metadata with MBIDs
        return {"enriched": True, "source": "MusicBrainz"}

    def _resolve_identity(self, audio_data: AudioMetadata) -> Any:  # IdentityResolutionResult
        """Resolve identity using audio metadata (placeholder)."""
        # In production, would call IdentityResolutionService
        # For now, return a mock result
        from mim.mcm.domain.identity_resolution import (
            IdentityResolutionResult,
            ResolutionResultStatus,
        )
        return IdentityResolutionResult(
            status=ResolutionResultStatus.RESOLVED,
            evidence=[],
            resolved_identity_id="mock-id",
            resolved_version_id=None,
            confidence=0.8,
            rationale="Mock resolution",
        )