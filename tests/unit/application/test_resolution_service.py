import tempfile
import os
import pytest

from mim.mcm.infrastructure.sqlite_db import create_database
from mim.mcm.infrastructure.repositories import (
    SQLiteIdentityRepository,
    SQLiteVersionRepository,
    SQLiteSourceRepository,
    SQLiteLibraryEntryRepository,
    SQLiteReleaseRepository,
    SQLiteResolutionRepository,
)
from mim.mcm.application.source_resolvers import (
    LocalSourceResolver,
    CacheSourceResolver,
    RemoteSourceResolver,
    DownloadSourceResolver,
    ResolverChain,
)
from mim.mcm.application.resolution_service import ResolutionService, ResolutionConfig
from mim.mcm.application.release_service import ReleaseService, create_sample_release
from mim.mcm.domain.identity import Identity
from mim.mcm.domain.version import Version
from mim.mcm.domain.source import Source, SourceType
from mim.mcm.domain.library import LibraryEntry, FileStatus
from mim.mcm.domain.release import Release, ReleaseTrack, ReleaseType
from mim.mcm.domain.resolution import Resolution, Evidence, EvidenceType
from mim.mcm.domain.confidence import Confidence
from mim.mcm.domain.availability import Availability, AvailabilityStatus


@pytest.fixture
def full_setup():
    """Setup completo com todos os repositórios."""
    tmp_db = tempfile.NamedTemporaryFile(delete=False).name
    db = create_database(tmp_db)
    conn = db._conn
    
    identity_repo = SQLiteIdentityRepository(conn)
    version_repo = SQLiteVersionRepository(conn)
    source_repo = SQLiteSourceRepository(conn)
    library_repo = SQLiteLibraryEntryRepository(conn)
    release_repo = SQLiteReleaseRepository(conn)
    resolution_repo = SQLiteResolutionRepository(conn)
    
    yield {
        "db": db,
        "conn": conn,
        "identity_repo": identity_repo,
        "version_repo": version_repo,
        "source_repo": source_repo,
        "library_repo": library_repo,
        "release_repo": release_repo,
        "resolution_repo": resolution_repo,
    }
    
    db.close()
    os.unlink(tmp_db)


def test_release_service_crud(full_setup):
    identity_repo = full_setup["identity_repo"]
    version_repo = full_setup["version_repo"]
    release_repo = full_setup["release_repo"]
    
    # Pre-req: identity AND versions (FK references versions table)
    identity_repo.add(Identity(id="id1", title="Test", artist="Artist"))
    version_repo.add(Version(id="id1", identity_id="id1", label="Test Version"))
    version_repo.add(Version(id="v1", identity_id="id1", label="Track 1"))
    version_repo.add(Version(id="v2", identity_id="id1", label="Track 2"))
    
    service = ReleaseService(release_repo)
    release, tracks = create_sample_release()
    
    service.add_release_with_tracks(release, tracks)
    
    fetched = service.get_release("rel1")
    assert fetched is not None
    assert fetched.title == "Example Album"
    assert fetched.release_type == ReleaseType.ALBUM
    
    fetched_tracks = service.get_tracks("rel1")
    assert len(fetched_tracks) == 2
    assert fetched_tracks[0].track_number == 1
    assert fetched_tracks[1].track_number == 2
    
    # Find by identity
    releases = service.find_releases_by_identity("id1")
    assert len(releases) == 1


def test_resolver_chain_priority(full_setup):
    """Testa que ResolverChain tenta em ordem: local -> cache -> remote -> download"""
    identity_repo = full_setup["identity_repo"]
    version_repo = full_setup["version_repo"]
    library_repo = full_setup["library_repo"]
    source_repo = full_setup["source_repo"]
    
    # Create hierarchy
    identity_repo.add(Identity(id="id1", title="T", artist="A"))
    version_repo.add(Version(id="v1", identity_id="id1", label="O"))
    
    # Create a source and library entry
    library_repo.add(LibraryEntry(id="le1", path="/music/song.mp3", status=FileStatus.PRESENT))
    source_repo.add(Source(id="le1", version_id="v1", source_type=SourceType.LOCAL))
    
    local_resolver = LocalSourceResolver(library_repo, source_repo)
    cache_resolver = CacheSourceResolver()
    remote_resolver = RemoteSourceResolver()
    download_resolver = DownloadSourceResolver()
    
    chain = ResolverChain([local_resolver, cache_resolver, remote_resolver, download_resolver])
    
    # Should resolve to local source
    result = chain.resolve("v1")
    assert result == "le1"
    
    # If local fails, should try cache
    chain2 = ResolverChain([cache_resolver, remote_resolver, download_resolver])
    result2 = chain2.resolve("v1")
    assert result2 is None  # cache returns None
    
    # If all fail, returns None
    chain3 = ResolverChain([cache_resolver, remote_resolver, download_resolver])
    result3 = chain3.resolve("nonexistent")
    assert result3 is None


def test_resolution_service_resolves_local(full_setup):
    """Testa resolução completa local com confidence >= 0.7"""
    identity_repo = full_setup["identity_repo"]
    version_repo = full_setup["version_repo"]
    source_repo = full_setup["source_repo"]
    library_repo = full_setup["library_repo"]
    resolution_repo = full_setup["resolution_repo"]
    
    # Setup hierarchy
    identity_repo.add(Identity(id="id1", title="Test Song", artist="Test Artist"))
    version_repo.add(Version(id="v1", identity_id="id1", label="Original"))
    
    # Create local source and library entry
    source_repo.add(Source(id="le1", version_id="v1", source_type=SourceType.LOCAL))
    library_repo.add(LibraryEntry(id="le1", path="/music/test.mp3", status=FileStatus.PRESENT))
    
    # Create resolver chain and service
    local_resolver = LocalSourceResolver(library_repo, source_repo)
    chain = ResolverChain([local_resolver])
    
    service = ResolutionService(
        version_repo=version_repo,
        source_repo=source_repo,
        resolution_repo=resolution_repo,
        source_resolver=chain,
        library_repo=library_repo,
        config=ResolutionConfig(confidence_threshold=0.7),
    )
    
    resolution = service.resolve_version("v1")
    
    assert resolution.source_id == "le1"
    assert resolution.confidence.value >= 0.7  # FILE_HASH = 0.9
    assert resolution.availability.status == AvailabilityStatus.AVAILABLE
    assert resolution.is_resolved() == True
    assert resolution.get_best_source_id() == "le1"


def test_resolution_service_missing_local(full_setup):
    """Testa que versão sem arquivo local não resolve (confidence baixa)."""
    identity_repo = full_setup["identity_repo"]
    version_repo = full_setup["version_repo"]
    source_repo = full_setup["source_repo"]
    library_repo = full_setup["library_repo"]
    resolution_repo = full_setup["resolution_repo"]
    
    identity_repo.add(Identity(id="id1", title="Test", artist="Artist"))
    version_repo.add(Version(id="v1", identity_id="id1", label="Original"))
    
    # Source exists but NO library entry (or MISSING)
    source_repo.add(Source(id="le1", version_id="v1", source_type=SourceType.LOCAL))
    library_repo.add(LibraryEntry(id="le1", path="/music/test.mp3", status=FileStatus.MISSING))
    
    local_resolver = LocalSourceResolver(library_repo, source_repo)
    chain = ResolverChain([local_resolver])
    
    service = ResolutionService(
        version_repo=version_repo,
        source_repo=source_repo,
        resolution_repo=resolution_repo,
        source_resolver=chain,
        library_repo=library_repo,
    )
    
    resolution = service.resolve_version("v1")
    
    # Only metadata match evidence (0.3) - below threshold
    assert resolution.source_id is None
    assert resolution.confidence.value == 0.3
    assert resolution.availability.status == AvailabilityStatus.UNKNOWN
    assert resolution.is_resolved() == False


def test_resolution_config_weights(full_setup):
    """Testa que pesos customizados funcionam."""
    identity_repo = full_setup["identity_repo"]
    version_repo = full_setup["version_repo"]
    source_repo = full_setup["source_repo"]
    library_repo = full_setup["library_repo"]
    resolution_repo = full_setup["resolution_repo"]
    
    identity_repo.add(Identity(id="id1", title="T", artist="A"))
    version_repo.add(Version(id="v1", identity_id="id1", label="Original"))
    source_repo.add(Source(id="le1", version_id="v1", source_type=SourceType.LOCAL))
    library_repo.add(LibraryEntry(id="le1", path="/music/test.mp3", status=FileStatus.PRESENT))
    
    local_resolver = LocalSourceResolver(library_repo, source_repo)
    chain = ResolverChain([local_resolver])
    
    # Custom weights
    config = ResolutionConfig(
        weights={
            EvidenceType.FILE_HASH: 0.5,  # Lower weight
            EvidenceType.METADATA_MATCH: 0.1,
        },
        confidence_threshold=0.7,
    )
    
    service = ResolutionService(
        version_repo=version_repo,
        source_repo=source_repo,
        resolution_repo=resolution_repo,
        source_resolver=chain,
        library_repo=library_repo,
        config=config,
    )
    
    resolution = service.resolve_version("v1")
    
    # With FILE_HASH=0.5 + METADATA=0.1 = 0.6 (but capped at 1.0, sum=0.6)
    # Actually the confidence calculation sums weights, so 0.5 + 0.1 = 0.6
    assert resolution.confidence.value == 0.6
    assert resolution.is_resolved() == False  # Below 0.7 threshold


def test_resolution_persists_and_retrieves(full_setup):
    """Testa que resolução é persistida e recuperada."""
    identity_repo = full_setup["identity_repo"]
    version_repo = full_setup["version_repo"]
    source_repo = full_setup["source_repo"]
    library_repo = full_setup["library_repo"]
    resolution_repo = full_setup["resolution_repo"]
    
    identity_repo.add(Identity(id="id1", title="T", artist="A"))
    version_repo.add(Version(id="v1", identity_id="id1", label="Original"))
    source_repo.add(Source(id="le1", version_id="v1", source_type=SourceType.LOCAL))
    library_repo.add(LibraryEntry(id="le1", path="/music/test.mp3", status=FileStatus.PRESENT))
    
    local_resolver = LocalSourceResolver(library_repo, source_repo)
    chain = ResolverChain([local_resolver])
    
    service = ResolutionService(
        version_repo=version_repo,
        source_repo=source_repo,
        resolution_repo=resolution_repo,
        source_resolver=chain,
        library_repo=library_repo,
    )
    
    # First resolution
    resolution1 = service.resolve_version("v1")
    resolution_id = resolution1.resolution_id
    
    # Retrieve from repo
    resolution2 = service.get_resolution(resolution_id)
    assert resolution2 is not None
    assert resolution2.resolution_id == resolution_id
    assert resolution2.source_id == "le1"
    assert len(resolution2.evidence) == len(resolution1.evidence)


def test_resolution_evidence_types(full_setup):
    """Testa coleta de diferentes tipos de evidence."""
    identity_repo = full_setup["identity_repo"]
    version_repo = full_setup["version_repo"]
    source_repo = full_setup["source_repo"]
    library_repo = full_setup["library_repo"]
    resolution_repo = full_setup["resolution_repo"]
    
    identity_repo.add(Identity(id="id1", title="T", artist="A"))
    version_repo.add(Version(id="v1", identity_id="id1", label="Original"))
    source_repo.add(Source(id="le1", version_id="v1", source_type=SourceType.LOCAL))
    library_repo.add(LibraryEntry(id="le1", path="/music/test.mp3", status=FileStatus.PRESENT))
    
    local_resolver = LocalSourceResolver(library_repo, source_repo)
    chain = ResolverChain([local_resolver])
    
    service = ResolutionService(
        version_repo=version_repo,
        source_repo=source_repo,
        resolution_repo=resolution_repo,
        source_resolver=chain,
        library_repo=library_repo,
    )
    
    resolution = service.resolve_version("v1")
    
    evidence_types = {e.type for e in resolution.evidence}
    assert EvidenceType.FILE_HASH in evidence_types
    assert EvidenceType.METADATA_MATCH in evidence_types
    
    # Check weights
    file_hash_evidence = next(e for e in resolution.evidence if e.type == EvidenceType.FILE_HASH)
    metadata_evidence = next(e for e in resolution.evidence if e.type == EvidenceType.METADATA_MATCH)
    assert file_hash_evidence.weight == 0.9
    assert metadata_evidence.weight == 0.3