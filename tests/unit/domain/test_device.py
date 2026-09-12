from mim.mcl.domain.device import Device

def test_same_capabilities_different_type():
    caps = {"play_audio", "download"}
    d1 = Device("d1", type="smartphone", capabilities=caps)
    d2 = Device("d2", type="tablet", capabilities=caps)
    assert d1.capabilities == d2.capabilities
