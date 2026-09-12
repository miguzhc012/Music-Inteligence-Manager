from mim.mcm.domain.materialization import Materialization, MaterializationState

def test_materialization_states():
    m1 = Materialization("src1", MaterializationState.UNAVAILABLE)
    m2 = Materialization("src1", MaterializationState.CACHED)
    m3 = Materialization("src1", MaterializationState.DOWNLOADED)
    assert m1.state == MaterializationState.UNAVAILABLE
    assert m2.state == MaterializationState.CACHED
    assert m3.state == MaterializationState.DOWNLOADED
