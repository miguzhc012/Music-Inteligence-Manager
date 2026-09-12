import pytest
from mim.mcm.domain.confidence import Confidence

def test_confidence_valid():
    c = Confidence(0.5)
    assert c.value == 0.5

def test_confidence_lower_bound():
    c = Confidence(0.0)
    assert c.value == 0.0

def test_confidence_upper_bound():
    c = Confidence(1.0)
    assert c.value == 1.0

def test_confidence_below_zero_raises():
    with pytest.raises(ValueError):
        Confidence(-0.1)

def test_confidence_above_one_raises():
    with pytest.raises(ValueError):
        Confidence(1.1)
