from mim.mcm.domain.availability import Availability, AvailabilityStatus
from mim.mcm.domain.confidence import Confidence

def test_availability_and_confidence_are_independent():
    a = Availability(AvailabilityStatus.AVAILABLE)
    c = Confidence(0.9)
    assert a.status == AvailabilityStatus.AVAILABLE
    assert c.value == 0.9

    a2 = Availability(AvailabilityStatus.STALE)
    assert a2.status != a.status
    assert c.value == 0.9

    c2 = Confidence(0.1)
    assert a.status == AvailabilityStatus.AVAILABLE
    assert c2.value == 0.1
