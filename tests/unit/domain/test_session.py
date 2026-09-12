from mim.mcl.domain.session import Session, SessionState

def test_session_contains_only_references():
    session = Session("s1", "src1", "dev1")
    assert isinstance(session.source_id, str)
    assert isinstance(session.device_id, str)
    assert not hasattr(session, "source")
    assert not hasattr(session, "device")
