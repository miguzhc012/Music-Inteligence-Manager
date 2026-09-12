import tempfile
import os
import pytest

from mim.mcm.infrastructure.sqlite_db import create_database
from mim.mcm.infrastructure.repositories import (
    SQLiteIdentityRepository,
    SQLiteVersionRepository,
    SQLiteSourceRepository,
)
from mim.mcm.domain.identity import Identity
from mim.mcm.domain.version import Version
from mim.mcm.domain.source import Source, SourceType


@pytest.fixture
def db():
    tmp_db = tempfile.NamedTemporaryFile(delete=False).name
    db = create_database(tmp_db)
    yield db
    db.close()
    os.unlink(tmp_db)


def test_identity_repository_crud(db):
    repo = SQLiteIdentityRepository(db._conn)
    
    identity = Identity(id="id1", title="Song Title", artist="Artist Name")
    repo.add(identity)
    
    fetched = repo.get("id1")
    assert fetched is not None
    assert fetched.id == "id1"
    assert fetched.title == "Song Title"
    assert fetched.artist == "Artist Name"
    
    # Update
    identity2 = Identity(id="id1", title="New Title", artist="New Artist")
    repo.add(identity2)
    fetched = repo.get("id1")
    assert fetched.title == "New Title"
    assert fetched.artist == "New Artist"
    
    # Non-existent
    assert repo.get("nonexistent") is None


def test_version_repository_crud(db):
    repo = SQLiteVersionRepository(db._conn)
    identity_repo = SQLiteIdentityRepository(db._conn)
    
    # Insert identity first (FK requirement)
    identity_repo.add(Identity(id="id1", title="Song Title", artist="Artist Name"))
    
    version = Version(id="v1", identity_id="id1", label="Original")
    repo.add(version)
    
    fetched = repo.get("v1")
    assert fetched is not None
    assert fetched.id == "v1"
    assert fetched.identity_id == "id1"
    assert fetched.label == "Original"
    
    # Update
    version2 = Version(id="v1", identity_id="id1", label="Remix")
    repo.add(version2)
    fetched = repo.get("v1")
    assert fetched.label == "Remix"
    
    # Non-existent
    assert repo.get("nonexistent") is None


def test_source_repository_crud(db):
    repo = SQLiteSourceRepository(db._conn)
    identity_repo = SQLiteIdentityRepository(db._conn)
    version_repo = SQLiteVersionRepository(db._conn)
    
    # Insert hierarchy (FK requirement)
    identity_repo.add(Identity(id="id1", title="T", artist="A"))
    version_repo.add(Version(id="v1", identity_id="id1", label="O"))
    
    source = Source(id="s1", version_id="v1", source_type=SourceType.LOCAL)
    repo.add(source)
    
    fetched = repo.get("s1")
    assert fetched is not None
    assert fetched.id == "s1"
    assert fetched.version_id == "v1"
    assert fetched.source_type == SourceType.LOCAL
    
    # Get by version
    sources = repo.get_by_version("v1")
    assert len(sources) == 1
    assert sources[0].id == "s1"
    
    # Multiple sources for same version
    source2 = Source(id="s2", version_id="v1", source_type=SourceType.REMOTE)
    repo.add(source2)
    sources = repo.get_by_version("v1")
    assert len(sources) == 2
    source_types = {s.source_type for s in sources}
    assert SourceType.LOCAL in source_types
    assert SourceType.REMOTE in source_types
    
    # Non-existent
    assert repo.get("nonexistent") is None