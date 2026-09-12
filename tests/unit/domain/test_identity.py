import pytest
from mim.mcm.domain.identity import Identity

def test_identity_creation():
    i = Identity("id1", "Música", "Artista")
    assert i.title == "Música"
    assert i.artist == "Artista"

def test_identity_frozen():
    i = Identity("id1", "Música", "Artista")
    with pytest.raises(AttributeError):
        i.title = "Outra"
