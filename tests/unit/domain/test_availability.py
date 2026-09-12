from mim.mcm.domain.availability import Availability, AvailabilityStatus

def test_availability_statuses():
    for status in AvailabilityStatus:
        a = Availability(status)
        assert a.status == status
