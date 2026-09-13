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
    SQLiteLyricsRepository,
    SQLiteMaterializationRepository,
    SQLiteDeviceStorageRepository,
    SQLiteHistoryRepository,
    SQLitePlaySessionRepository,
    SQLiteDiscoveryRepository,
    SQLiteAcousticProfileRepository,
    SQLiteRecommendationRepository,
    SQLiteUserTasteProfileRepository,
    SQLiteAudioFeatureRepository,
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
from mim.mcm.application.lyrics_service import LyricsService, LocalLyricsProvider, EmbeddedLyricsProvider
from mim.mcm.application.discovery_service import DiscoveryService, AcousticAnalysisService
from mim.mcm.application.recommendation_service import RecommendationService, UserTasteService
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
lyrics_repo = SQLiteLyricsRepository(conn)
materialization_repo = SQLiteMaterializationRepository(conn)
device_storage_repo = SQLiteDeviceStorageRepository(conn)
history_repo = SQLiteHistoryRepository(conn)
session_repo = SQLitePlaySessionRepository(conn)
discovery_repo = SQLiteDiscoveryRepository(conn)
acoustic_repo = SQLiteAcousticProfileRepository(conn)
recommendation_repo = SQLiteRecommendationRepository(conn)
taste_repo = SQLiteUserTasteProfileRepository(conn)
audio_feature_repo = SQLiteAudioFeatureRepository(conn)

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

# Lyrics services
local_lyrics_provider = LocalLyricsProvider(library_repo)
embedded_lyrics_provider = EmbeddedLyricsProvider(library_repo, source_repo)

lyrics_service = LyricsService(
    lyrics_repo=lyrics_repo,
    providers=[local_lyrics_provider, embedded_lyrics_provider],
    version_repo=version_repo,
    identity_repo=identity_repo,
)

# Discovery services
discovery_service = DiscoveryService(
    discovery_repo=discovery_repo,
    version_repo=version_repo,
    identity_repo=identity_repo,
)

acoustic_service = AcousticAnalysisService(
    acoustic_repo=acoustic_repo,
)

# Recommendation services
recommendation_service = RecommendationService(
    recommendation_repo=recommendation_repo,
    user_taste_repo=taste_repo,
    audio_feature_repo=audio_feature_repo,
    history_repo=history_repo,
)

user_taste_service = UserTasteService(
    taste_repo=taste_repo,
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
    print("\nMIM Music Intelligence Manager - Rodando!")
    print("=" * 50)
    print("Serviços disponíveis:")
    print("  [Library]    LibraryService, Scanner")
    print("  [Resolution] ResolutionService, ResolverChain")
    print("  [Playback]   PlaybackService (queue, repeat, shuffle)")
    print("  [Lyrics]     LyricsService (synced/unsynced)")
    print("  [Discovery]  DiscoveryService, AcousticAnalysis")
    print("  [Recommend]  RecommendationService, UserTasteService")
    print("  [History]    History tracking, Listening stats")
    print("=" * 50)
    pass
finally:
    watcher.stop()
    db.close()