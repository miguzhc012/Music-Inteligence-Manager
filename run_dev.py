from pathlib import Path

from mim.mcm.infrastructure.sqlite_db import create_database
from mim.mcm.infrastructure.repositories import (
    SQLiteIdentityRepository,
    SQLiteVersionRepository,
    SQLiteSourceRepository,
    SQLiteLibraryEntryRepository,
    SQLiteReleaseRepository,
    SQLiteResolutionRepository,
    SQLiteQueueRepository,
    SQLitePlaybackStateRepository,
)
from mim.mcm.application.library_service import LibraryService, Scanner
from mim.mcm.application.source_resolvers import (
    LocalSourceResolver,
    CacheSourceResolver,
    RemoteSourceResolver,
    DownloadSourceResolver,
    ResolverChain,
)
from mim.mcm.application.resolution_service import ResolutionService, ResolutionConfig
from mim.mcm.application.release_service import ReleaseService
from mim.mcm.application.playback_service import PlaybackService, MutagenAudioBackend, ResolutionApplicationService
from mim.mcm.infrastructure.watcher import DirectoryWatcher


# 1. Configurar infraestrutura
db = create_database("library.db")
conn = db._conn

identity_repo = SQLiteIdentityRepository(conn)
version_repo = SQLiteVersionRepository(conn)
source_repo = SQLiteSourceRepository(conn)
library_repo = SQLiteLibraryEntryRepository(conn)
release_repo = SQLiteReleaseRepository(conn)
resolution_repo = SQLiteResolutionRepository(conn)
queue_repo = SQLiteQueueRepository(conn)
state_repo = SQLitePlaybackStateRepository(conn)

# 2. Configurar serviços de aplicação
library_service = LibraryService(library_repo)

# Resolver chain (local first - cost zero priority)
local_resolver = LocalSourceResolver(library_repo, source_repo)
cache_resolver = CacheSourceResolver()
remote_resolver = RemoteSourceResolver()
download_resolver = DownloadSourceResolver()

resolver_chain = ResolverChain([
    local_resolver,
    cache_resolver,
    remote_resolver,
    download_resolver,
])

resolution_config = ResolutionConfig(
    confidence_threshold=0.7,
)

resolution_service = ResolutionService(
    version_repo=version_repo,
    source_repo=source_repo,
    resolution_repo=resolution_repo,
    source_resolver=resolver_chain,
    library_repo=library_repo,
    config=resolution_config,
)

release_service = ReleaseService(release_repo)

# Playback services
audio_backend = MutagenAudioBackend()
playback_service = PlaybackService(
    queue_repo=queue_repo,
    state_repo=state_repo,
    source_repo=source_repo,
    library_repo=library_repo,
    audio_backend=audio_backend,
)

resolution_app_service = ResolutionApplicationService(
    resolution_service=resolution_service,
    playback_service=playback_service,
    source_repo=source_repo,
    library_repo=library_repo,
)

# 3. Escaneamento inicial
musicas_dir = "/home/miguel/Músicas"
scanner = Scanner(library_service)

if Path(musicas_dir).exists():
    scanner.scan_directory(musicas_dir)
    print(f"Escaneado: {musicas_dir}")
else:
    print(f"Diretório não existe (ok para testes): {musicas_dir}")

# 4. Monitoramento em tempo real
watcher = DirectoryWatcher(musicas_dir, library_service)
watcher.start()

try:
    # App rodando - aqui viria a UI/API/CLI
    print("MIM Fase 3 rodando. Serviços disponíveis:")
    print("  - LibraryService (library)")
    print("  - ReleaseService (release)")
    print("  - ResolutionService (resolution)")
    print("  - ResolverChain (local->cache->remote->download)")
    print("  - PlaybackService (queue, repeat, shuffle, seek, volume)")
    print("  - ResolutionApplicationService (resolve + play)")
    pass
finally:
    watcher.stop()
    db.close()