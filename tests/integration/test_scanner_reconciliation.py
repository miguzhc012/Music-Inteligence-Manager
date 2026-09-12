import os
import tempfile
from pathlib import Path

import pytest

from mim.mcm.infrastructure.sqlite_db import create_database
from mim.mcm.infrastructure.repositories import SQLiteLibraryEntryRepository
from mim.mcm.application.library_service import LibraryService, Scanner
from mim.mcm.domain.library import FileStatus

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)

@pytest.fixture
def repo():
    tmp_db = tempfile.NamedTemporaryFile(delete=False).name
    db = create_database(tmp_db)
    conn = db._conn
    repo = SQLiteLibraryEntryRepository(conn)
    yield repo
    db.close()
    os.unlink(tmp_db)

def test_scanner_marks_missing_and_present(temp_dir: Path, repo):
    file1 = temp_dir / "song1.mp3"
    file1.write_bytes(b"fake")

    service = LibraryService(repo)
    service.register_file(str(file1))

    scanner = Scanner(service)
    scanner.scan_directory(str(temp_dir))
    entries = service.get_entries()
    assert len(entries) == 1
    assert entries[0].path == str(file1)
    assert entries[0].status == FileStatus.PRESENT

    file1.unlink()

    scanner.scan_directory(str(temp_dir))
    entries = service.get_entries()
    assert len(entries) == 1
    assert entries[0].status == FileStatus.MISSING

    file1.write_bytes(b"fake")

    scanner.scan_directory(str(temp_dir))
    entries = service.get_entries()
    assert len(entries) == 1
    assert entries[0].status == FileStatus.PRESENT
