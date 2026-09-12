import pytest
from mim.mcm.domain.library import LibraryEntry, FileStatus

def test_library_entry_creation():
    entry = LibraryEntry("id1", "/music/artist - song.mp3", FileStatus.PRESENT)
    assert entry.id == "id1"
    assert entry.path == "/music/artist - song.mp3"
    assert entry.status == FileStatus.PRESENT

def test_library_entry_status_enum():
    assert FileStatus.PRESENT.value == "PRESENT"
    assert FileStatus.MISSING.value == "MISSING"

def test_library_entry_immutable():
    entry = LibraryEntry("id1", "/path", FileStatus.PRESENT)
    with pytest.raises(AttributeError):
        entry.status = FileStatus.MISSING
