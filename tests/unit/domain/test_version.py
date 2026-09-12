import pytest
from mim.mcm.domain.version import Version

def test_version_creation():
    v = Version("v1", "id1", "acoustic")
    assert v.identity_id == "id1"
    assert v.label == "acoustic"
