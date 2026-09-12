import pytest
from mim.mcm.domain.resolution import Resolution, Evidence, EvidenceType
from mim.mcm.domain.confidence import Confidence
from mim.mcm.domain.availability import Availability, AvailabilityStatus

def test_resolution_initial_state():
    res = Resolution(version_id="ver-1")
    assert res.version_id == "ver-1"
    assert res.confidence.value == 0.0
    assert res.availability.status == AvailabilityStatus.UNKNOWN
    assert len(res.evidence) == 0

def test_add_evidence_recalculates_confidence():
    res = Resolution(version_id="ver-1")
    res.add_evidence(Evidence(type=EvidenceType.METADATA_MATCH, weight=0.5, description="Match title"))
    assert res.confidence.value == 0.5

    res.add_evidence(Evidence(type=EvidenceType.ACOUSTIC_FINGERPRINT, weight=0.6, description="Match fingerprint"))
    # sum is 1.1, but max is 1.0
    assert res.confidence.value == 1.0

def test_is_resolved():
    res = Resolution(
        version_id="ver-1",
        source_id="src-1",
        availability=Availability(AvailabilityStatus.AVAILABLE)
    )

    # Confidence 0.0 < 0.7
    assert not res.is_resolved()

    res.add_evidence(Evidence(type=EvidenceType.ISRC_MATCH, weight=0.8, description="ISRC Match"))
    # Confidence 0.8 >= 0.7 and status is AVAILABLE
    assert res.is_resolved()
    assert res.get_best_source_id() == "src-1"

def test_get_best_source_id_none_if_unresolved():
    res = Resolution(version_id="ver-1", source_id="src-1")
    assert res.get_best_source_id() is None
