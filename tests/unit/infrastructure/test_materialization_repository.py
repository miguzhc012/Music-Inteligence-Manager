import tempfile
import os
import pytest

from mim.mcm.infrastructure.sqlite_db import create_database
from mim.mcm.infrastructure.repositories import (
    SQLiteIdentityRepository,
    SQLiteVersionRepository,
    SQLiteSourceRepository,
    SQLiteMaterializationRepository,
    SQLiteDeviceStorageRepository,
)
from mim.mcm.domain.identity import Identity
from mim.mcm.domain.version import Version
from mim.mcm.domain.source import Source, SourceType
from mim.mcm.domain.materialization import (
    Materialization, MaterializationState, MaterializationQuality, DeviceStorage
)


@pytest.fixture
def mat_setup():
    """Setup para testes de materialização."""
    tmp_db = tempfile.NamedTemporaryFile(delete=False).name
    db = create_database(tmp_db)
    conn = db._conn
    
    identity_repo = SQLiteIdentityRepository(conn)
    version_repo = SQLiteVersionRepository(conn)
    source_repo = SQLiteSourceRepository(conn)
    mat_repo = SQLiteMaterializationRepository(conn)
    storage_repo = SQLiteDeviceStorageRepository(conn)
    
    # Setup hierarchy
    identity_repo.add(Identity(id="id1", title="Test Song", artist="Test Artist"))
    version_repo.add(Version(id="v1", identity_id="id1", label="Original"))
    source_repo.add(Source(id="s1", version_id="v1", source_type=SourceType.LOCAL))
    source_repo.add(Source(id="s2", version_id="v1", source_type=SourceType.REMOTE))
    
    yield {
        "db": db,
        "conn": conn,
        "identity_repo": identity_repo,
        "version_repo": version_repo,
        "source_repo": source_repo,
        "mat_repo": mat_repo,
        "storage_repo": storage_repo,
    }
    
    db.close()
    os.unlink(tmp_db)


def test_materialization_domain_entities():
    """Testa entidades de domínio de materialização."""
    # Enums
    assert MaterializationState.DOWNLOADED.value == "downloaded"
    assert MaterializationQuality.LOSSLESS.value == "lossless"
    
    # Materialization
    mat = Materialization(
        source_id="s1",
        state=MaterializationState.DOWNLOADED,
        file_path="/path/to/song.flac",
        device_id="dev1",
        quality=MaterializationQuality.LOSSLESS,
        format="flac",
        bitrate=1411,
        sample_rate=44100,
        bit_depth=16,
        file_size=30000000,
        checksum="abc123hash",
    )
    
    assert mat.is_available_locally is True
    assert mat.is_permanent is True
    assert mat.file_path == "/path/to/song.flac"
    
    # DeviceStorage
    storage = DeviceStorage(
        device_id="dev1",
        total_bytes=1000000000,
        free_bytes=400000000,
        path="/storage",
    )
    
    assert storage.used_bytes == 600000000
    assert storage.usage_percent == 60.0


def test_materialization_repository_crud(mat_setup):
    """Testa CRUD do MaterializationRepository."""
    mat_repo = mat_setup["mat_repo"]
    
    mat = Materialization(
        source_id="s1",
        state=MaterializationState.DOWNLOADED,
        file_path="/path/to/song.flac",
        device_id="dev1",
        quality=MaterializationQuality.LOSSLESS,
        format="flac",
        bitrate=1411,
        sample_rate=44100,
        bit_depth=16,
        file_size=30000000,
        checksum="abc123hash",
    )
    
    mat_repo.add(mat)
    
    # Get by source_id
    fetched = mat_repo.get("s1")
    assert fetched is not None
    assert fetched.source_id == "s1"
    assert fetched.state == MaterializationState.DOWNLOADED
    assert fetched.quality == MaterializationQuality.LOSSLESS
    
    # Get by source_id and device_id
    fetched_dev = mat_repo.get("s1", "dev1")
    assert fetched_dev is not None
    assert fetched_dev.device_id == "dev1"
    
    # Get available for source
    available = mat_repo.get_available_for_source("s1")
    assert len(available) == 1
    
    # Get by device
    by_dev = mat_repo.get_by_device("dev1")
    assert len(by_dev) == 1
    
    # Delete
    mat_repo.delete("s1", "dev1")
    assert mat_repo.get("s1", "dev1") is None


def test_device_storage_repository_crud(mat_setup):
    """Testa CRUD do DeviceStorageRepository."""
    storage_repo = mat_setup["storage_repo"]
    
    storage = DeviceStorage(
        device_id="dev1",
        total_bytes=1000000000,
        free_bytes=400000000,
        path="/storage/music",
    )
    
    storage_repo.add(storage)
    
    # Get
    fetched = storage_repo.get("dev1")
    assert fetched is not None
    assert fetched.device_id == "dev1"
    assert fetched.total_bytes == 1000000000
    assert fetched.free_bytes == 400000000
    
    # Update
    updated_storage = DeviceStorage(
        device_id="dev1",
        total_bytes=1000000000,
        free_bytes=300000000,  # Space reduced
        path="/storage/music",
    )
    storage_repo.update(updated_storage)
    
    fetched = storage_repo.get("dev1")
    assert fetched.free_bytes == 300000000
    
    # List all
    all_storage = storage_repo.list_all()
    assert len(all_storage) == 1
    
    # Delete
    storage_repo.delete("dev1")
    assert storage_repo.get("dev1") is None