"""
Application service for audio extraction.
"""
from typing import Optional, Callable
from functools import lru_cache

from mim.mcm.domain.audio_metadata import AudioExtractionService, AudioMetadata


class AudioExtractionApplicationService:
    """
    Application service for extracting audio metadata.
    Uses the domain service and optionally caches results.
    """

    def __init__(self, domain_service: Optional[AudioExtractionService] = None, enable_cache: bool = True, max_cache_size: int = 1000):
        self._domain_service = domain_service or AudioExtractionService(enable_cache=enable_cache, max_cache_size=max_cache_size)
        if enable_cache:
            self._extract_cached: Callable[[str], AudioMetadata] = lru_cache(maxsize=max_cache_size)(self._extract)
        else:
            self._extract_cached = self._extract

    def extract(self, path: str) -> AudioMetadata:
        """Extract audio metadata with optional caching."""
        return self._extract_cached(path)

    def _extract(self, path: str) -> AudioMetadata:
        return self._domain_service.extract(path)

    def get_file_hash(self, path: str, algorithm: str = "sha256") -> str:
        """Get file hash using the domain service."""
        return self._domain_service.get_file_hash(path, algorithm)