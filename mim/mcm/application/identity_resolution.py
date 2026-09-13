"""
IdentityResolutionService - Resolve identity from audio file using multiple strategies.
"""
from dataclasses import dataclass
from typing import Optional, List
from uuid import uuid4

from mim.mcm.domain.audio_metadata import AudioExtractionService, AudioMetadata
from mim.mcm.domain.identity_resolution import (
    IdentityResolutionResult,
    ResolutionEvidence,
    ResolutionStrategy,
    ResolutionResultStatus,
    IdentityResolutionConfig,
)
from mim.mcm.domain.identity import Identity
from mim.mcm.domain.version import Version
from mim.mcm.domain.source import Source, SourceType
from mim.mcm.domain.ports import (
    IdentityRepository,
    VersionRepository,
    SourceRepository,
)
from mim.mcm.domain.materialization import MaterializationState


class IdentityResolutionService:
    """
    Resolve identity from audio file using multiple strategies:
    1. Exact file hash (SHA256)
    2. ID3/Vorbis tags (title/artist/album)
    3. ISRC match
    4. MusicBrainz IDs
    3. AcoustID fingerprint (if available)
    """

    def __init__(
        self,
        audio_extraction_service: AudioExtractionService,
        identity_repo: IdentityRepository,
        version_repo: VersionRepository,
        source_repo: SourceRepository,
        config: Optional[IdentityResolutionConfig] = None,
    ):
        self._audio_service = audio_extraction_service
        self._identity_repo = identity_repo
        self._version_repo = version_repo
        self._source_repo = source_repo
        self._config = config or IdentityResolutionConfig()

    def resolve_from_file(self, file_path: str) -> IdentityResolutionResult:
        """
        Resolve identity from an audio file.
        Returns IdentityResolutionResult with evidence and confidence.
        """
        # Extract audio metadata
        metadata = self._audio_service.extract(file_path)
        file_hash = self._audio_service.get_file_hash(file_path)

        evidence_list = []

        # Strategy 1: Exact file hash (highest confidence)
        if file_hash:
            identity_by_hash = self._get_identity_by_file_hash(file_hash)
            if identity_by_hash:
                evidence_list.append(
                    ResolutionEvidence(
                        strategy=ResolutionStrategy.EXACT_HASH,
                        weight=self._config.hash_threshold,
                        score=1.0,
                        description=f"Exact file hash match: {file_hash[:16]}...",
                        source_data={"file_hash": file_hash},
                        confidence=1.0,
                    )
                )

        # Strategy 2: Tags match (title/artist/album)
        if metadata.title or metadata.artist:
            tags_evidence = self._resolve_from_tags(metadata)
            if tags_evidence:
                evidence_list.append(tags_evidence)

        # Strategy 3: ISRC match
        if metadata.isrc:
            isrc_evidence = self._resolve_from_isrc(metadata.isrc)
            if isrc_evidence:
                evidence_list.append(isrc_evidence)

        # Strategy 4: MusicBrainz IDs
        mbid_evidence = self._resolve_from_musicbrainz_ids(metadata)
        if mbid_evidence:
            evidence_list.append(mbid_evidence)

        # Strategy 5: AcoustID fingerprint (placeholder)
        # if metadata.acoustid_id:
        #     acoustid_evidence = self._resolve_from_acoustid(metadata.acoustid_id)
        #     if acoustid_evidence:
        #         evidence_list.append(acoustid_evidence)

        # Aggregate evidence
        if not evidence_list:
            return IdentityResolutionResult(
                status=ResolutionResultStatus.UNRESOLVED,
                evidence=[],
                confidence=0.0,
                rationale="No evidence found",
            )

        # Check for conflicts (multiple identities with high confidence)
        identities = self._identify_candidates(evidence_list)
        if len(identities) > 1:
            return IdentityResolutionResult(
                status=ResolutionResultStatus.CONFLICT,
                evidence=evidence_list,
                confidence=0.0,
                rationale=f"Multiple identities found: {[i.id for i in identities]}",
                conflict_details=f"Identities: {[i.id for i in identities]}",
            )

        # If single identity, calculate final confidence
        if identities:
            identity = identities[0]
            # Calculate weighted average of evidence scores
            total_weight = sum(e.weight for e in evidence_list)
            if total_weight > 0:
                weighted_score = sum(e.adjusted_score for e in evidence_list) / total_weight
            else:
                weighted_score = 0.0

            # Determine best version/source for this identity
            best_version, best_source = self._find_best_version_and_source(identity.id)

            return IdentityResolutionResult(
                status=ResolutionResultStatus.RESOLVED,
                evidence=evidence_list,
                resolved_identity_id=identity.id,
                resolved_version_id=best_version.id if best_version else None,
                confidence=weighted_score,
                rationale=f"Resolved via {len(evidence_list)} evidence strands",
            )

        return IdentityResolutionResult(
            status=ResolutionResultStatus.UNRESOLVED,
            evidence=evidence_list,
            confidence=0.0,
            rationale="No identity matched evidence",
        )

    def _get_identity_by_file_hash(self, file_hash: str) -> Optional[Identity]:
        """Lookup identity by exact file hash (stored in identity metadata)."""
        # This would require a reverse lookup table; for now return None
        # In production, we'd maintain a hash->identity mapping
        return None

    def _resolve_from_tags(self, metadata: AudioMetadata) -> Optional[ResolutionEvidence]:
        """Resolve identity from ID3/Vorbis tags."""
        if not metadata.title and not metadata.artist:
            return None

        # Search for identities matching title/artist
        # This is simplified - in production would use fuzzy search
        identities = self._identity_repo.get_by_title_and_artist(
            metadata.title or "", metadata.artist or ""
        )
        if identities:
            # Take best match (first for now)
            identity = identities[0]
            # Score based on match quality
            score = 0.8  # Base score for tag match
            if metadata.album and hasattr(identity, "album") and identity.album == metadata.album:
                score = 0.9  # Higher if album matches
            return ResolutionEvidence(
                strategy=ResolutionStrategy.TAGS_MATCH,
                weight=self._config.tags_weight,
                score=score,
                description=f"Tag match: '{metadata.title}' by '{metadata.artist}'",
                source_data={"title": metadata.title, "artist": metadata.artist},
                confidence=score * self._config.tags_weight,
            )
        return None

    def _resolve_from_isrc(self, isrc: str) -> Optional[ResolutionEvidence]:
        """Resolve identity from ISRC."""
        # ISRC should be unique to a recording
        # In production, we'd have an ISRC index
        return None  # Placeholder

    def _resolve_from_musicbrainz_ids(self, metadata: AudioMetadata) -> Optional[ResolutionEvidence]:
        """Resolve from MusicBrainz IDs."""
        # Check if we have any MBID
        mbids = [
            metadata.musicbrainz_track_id,
            metadata.musicbrainz_artist_id,
            metadata.musicbrainz_release_id,
        ]
        if any(mbids):
            return ResolutionEvidence(
                strategy=ResolutionStrategy.MUSICBRAINZ_MBD,
                weight=self._config.mbid_weight,
                score=0.9,  # High confidence for MBID match
                description=f"MusicBrainz ID match: {metadata.musicbrainz_track_id or 'unknown'}",
                source_data={
                    "track_id": metadata.musicbrainz_track_id,
                    "artist_id": metadata.musicbrainz_artist_id,
                    "release_id": metadata.musicbrainz_release_id,
                },
                confidence=0.9 * self._config.mbid_weight,
            )
        return None

    def _identify_candidates(self, evidence_list: List[ResolutionEvidence]) -> List[Identity]:
        """Identify which identities are supported by evidence."""
        # Simplified - return all identities for now
        # In production, would intersect evidence sets
        identities = []
        for evidence in evidence_list:
            if evidence.source_data.get("title") and evidence.source_data.get("artist"):
                identities = self._identity_repo.get_by_title_and_artist(
                    evidence.source_data["title"], evidence.source_data["artist"]
                )
                if identities:
                    break
        return identities

    def _find_best_version_and_source(self, identity_id: str) -> tuple[Optional[Version], Optional[Source]]:
        """Find the best version and source for an identity."""
        versions = self._version_repo.get_by_identity(identity_id)
        if not versions:
            return None, None

        best_version = None
        best_source = None
        best_score: float = -1.0

        for version in versions:
            sources = self._source_repo.get_by_version(version.id)
            for source in sources:
                # Score based on source type preference
                source_score = {
                    SourceType.LOCAL: 1.0,
                    SourceType.DOWNLOAD: 0.8,
                    SourceType.REMOTE: 0.5,
                    SourceType.UNKNOWN: 0.1,
                }.get(source.source_type, 0.0)

                # Prefer higher quality materializations
                mat_score = 0.0
                # This would query MaterializationRepository

                total_score = source_score + mat_score
                if total_score > best_score:
                    best_score = total_score
                    best_version = version
                    best_source = source

        return best_version, best_source


class IdentityResolutionApplicationService:
    """
    Application service that orchestrates identity resolution.
    """

    def __init__(
        self,
        audio_extraction_service: AudioExtractionService,
        identity_repo: IdentityRepository,
        version_repo: VersionRepository,
        source_repo: SourceRepository,
        materialization_repo,  # Will be implemented later
        config: Optional[IdentityResolutionConfig] = None,
    ):
        self._domain_service = IdentityResolutionService(
            audio_extraction_service=audio_extraction_service,
            identity_repo=identity_repo,
            version_repo=version_repo,
            source_repo=source_repo,
            config=config,
        )
        self._materialization_repo = materialization_repo

    def resolve_and_enrich(self, file_path: str) -> IdentityResolutionResult:
        """Resolve identity and enrich with materialization info."""
        result = self._domain_service.resolve_from_file(file_path)
        if result.is_resolved and result.resolved_version_id:
            # Try to get best materialization
            # This would query MaterializationRepository for best state
            pass
        return result