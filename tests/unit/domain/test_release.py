import pytest
from mim.mcm.domain.release import Release, ReleaseTrack, ReleaseType

def test_release_creation():
    release = Release(
        id="rel-1",
        identity_id="id-1",
        title="Album Title",
        release_type=ReleaseType.ALBUM,
        release_date="2026-01-01",
        label="Test Label",
        catalog_number="CAT-001"
    )
    assert release.title == "Album Title"
    assert release.release_type == ReleaseType.ALBUM
    assert release.release_date == "2026-01-01"

def test_release_track_creation():
    track = ReleaseTrack(
        id="trk-1",
        release_id="rel-1",
        version_id="ver-1",
        track_number=1,
        disc_number=1,
        duration_ms=240000,
        isrc="US1234567890",
        explicit=False
    )
    assert track.track_number == 1
    assert track.version_id == "ver-1"
    assert track.isrc == "US1234567890"
