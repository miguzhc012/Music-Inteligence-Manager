import pytest
from mim.mcm.domain.source import Source, SourceType

def test_source_creation():
    s = Source("src1", "v1", SourceType.LOCAL)
    assert s.version_id == "v1"
    assert s.source_type == SourceType.LOCAL
