import pytest
from unittest.mock import MagicMock

from mim.mcm.application.library_service import LibraryService
from mim.mcm.domain.library import LibraryEntry, FileStatus

def test_register_new_file():
    repo = MagicMock()
    repo.get_by_path.return_value = None
    service = LibraryService(repo)
    entry = service.register_file("/tmp/test.mp3")
    assert entry.status == FileStatus.PRESENT
    repo.add.assert_called_once()

def test_mark_missing_updates_status():
    repo = MagicMock()
    existing = LibraryEntry("id1", "/tmp/test.mp3", FileStatus.PRESENT)
    repo.get_by_path.return_value = existing
    service = LibraryService(repo)
    service.mark_missing("/tmp/test.mp3")
    repo.update_status.assert_called_once_with("id1", FileStatus.MISSING)

def test_mark_present_existing():
    repo = MagicMock()
    existing = LibraryEntry("id1", "/tmp/test.mp3", FileStatus.MISSING)
    repo.get_by_path.return_value = existing
    service = LibraryService(repo)
    entry = service.mark_present("/tmp/test.mp3")
    assert entry.status == FileStatus.PRESENT
    repo.update_status.assert_called_once_with("id1", FileStatus.PRESENT)
