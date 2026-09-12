from mim.mcm.infrastructure.sqlite_db import create_database
from mim.mcm.infrastructure.repositories import SQLiteLibraryEntryRepository
from mim.mcm.application.library_service import LibraryService, Scanner
from mim.mcm.infrastructure.watcher import DirectoryWatcher

# 1. Configurar infraestrutura
db = create_database("library.db")
repo = SQLiteLibraryEntryRepository(db._conn)
service = LibraryService(repo)

musicas_dir = "/home/miguel/Músicas"

# 2. Escaneamento inicial (reconciliação ao abrir o app)
scanner = Scanner(service)
scanner.scan_directory(musicas_dir)

# 3. Iniciar monitoramento em tempo real
watcher = DirectoryWatcher(musicas_dir, service)
watcher.start()

try:
    # App rodando...
    pass
finally:
    watcher.stop()
    db.close()