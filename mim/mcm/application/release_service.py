from dataclasses import dataclass
from typing import Optional, List

from mim.mcm.domain.release import Release, ReleaseTrack, ReleaseType
from mim.mcm.domain.ports import ReleaseRepository


@dataclass
class ReleaseService:
    """Serviço de aplicação para gerenciar Releases e ReleaseTracks."""

    repo: ReleaseRepository

    def add_release(self, release: Release) -> None:
        """Adiciona um Release."""
        self.repo.add_release(release)

    def add_track(self, track: ReleaseTrack) -> None:
        """Adiciona uma faixa a um Release."""
        self.repo.add_track(track)

    def add_release_with_tracks(self, release: Release, tracks: List[ReleaseTrack]) -> None:
        """Adiciona Release e suas faixas atomicamente."""
        self.repo.add_release(release)
        for track in tracks:
            self.repo.add_track(track)

    def get_release(self, release_id: str) -> Optional[Release]:
        """Obtém Release por ID."""
        return self.repo.get_release(release_id)

    def get_tracks(self, release_id: str) -> List[ReleaseTrack]:
        """Obtém todas as faixas de um Release."""
        return self.repo.get_tracks_by_release(release_id)

    def get_release_with_tracks(self, release_id: str) -> Optional[tuple[Release, List[ReleaseTrack]]]:
        """Obtém Release com suas faixas."""
        release = self.repo.get_release(release_id)
        if not release:
            return None
        tracks = self.repo.get_tracks_by_release(release_id)
        return (release, tracks)

    def find_releases_by_identity(self, identity_id: str) -> List[Release]:
        """Busca todos os Releases de uma Identity."""
        return self.repo.get_releases_by_identity(identity_id)


def create_sample_release() -> tuple[Release, List[ReleaseTrack]]:
    """Helper para criar release de exemplo."""
    release = Release(
        id="rel1",
        identity_id="id1",
        title="Example Album",
        release_type=ReleaseType.ALBUM,
        release_date="2024-01-15",
        label="Example Label",
        catalog_number="EX-001",
        cover_url=None,
    )
    tracks = [
        ReleaseTrack(
            id="trk1",
            release_id="rel1",
            version_id="v1",
            track_number=1,
            disc_number=1,
            duration_ms=180000,
            isrc="USRC12345678",
            explicit=False,
        ),
        ReleaseTrack(
            id="trk2",
            release_id="rel1",
            version_id="v2",
            track_number=2,
            disc_number=1,
            duration_ms=210000,
            isrc="USRC12345679",
            explicit=False,
        ),
    ]
    return release, tracks