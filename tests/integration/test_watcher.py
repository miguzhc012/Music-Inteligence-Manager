import os
import time
import tempfile
from pathlib import Path

import pytest

from mim.mcm.infrastructure.sqlite_db import create_database
from mim.mcm.infrastructure.repositories import SQLiteLibraryEntryRepository
from mim.mcm.application.library_service import LibraryService
from mim.mcm.infrastructure.watcher import DirectoryWatcher
from mim.mcm.domain.library import FileStatus


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def service_and_watcher(temp_dir: Path):
    tmp_db = tempfile.NamedTemporaryFile(delete=False).name
    db = create_database(tmp_db)
    repo = SQLiteLibraryEntryRepository(db._conn)
    service = LibraryService(repo)
    
    watcher = DirectoryWatcher(str(temp_dir), service)
    watcher.start()

    yield service, temp_dir

    watcher.stop()
    db.close()
    if os.path.exists(tmp_db):
        os.unlink(tmp_db)


def test_watcher_detects_created_and_deleted_files(service_and_watcher):
    service, temp_dir = service_and_watcher

    # 1. Criar um arquivo de áudio novo na pasta monitorada
    audio_file = temp_dir / "track1.opus"
    audio_file.write_bytes(b"fake audio bytes")

    # Aguarda pequeno intervalo para o watchdog (assíncrono) processar o evento
    time.sleep(0.3)

    entries = service.get_entries()
    assert len(entries) == 1
    assert entries[0].path == str(audio_file.resolve())
    assert entries[0].status == FileStatus.PRESENT

    # 2. Deletar o arquivo
    audio_file.unlink()

    time.sleep(0.3)

    entries = service.get_entries()
    assert len(entries) == 1
    assert entries[0].status == FileStatus.MISSING