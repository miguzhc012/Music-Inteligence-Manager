from mim.mcl.domain.permission import Subject, SubjectType, Permission

def test_permission_creation():
    subject = Subject("user1", SubjectType.USER)
    perm = Permission(subject_id=subject.id, action="play", resource="src1")
    assert perm.subject_id == "user1"
    assert perm.action == "play"
    assert perm.resource == "src1"
