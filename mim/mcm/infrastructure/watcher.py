from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from mim.mcm.application.library_service import LibraryService, DEFAULT_AUDIO_EXTENSIONS


class LibraryWatcherHandler(FileSystemEventHandler):
    """Handler do watchdog que reage a mudanças de arquivos na pasta

    e envia os comandos correspondentes para o LibraryService.
    """

    def __init__(self, library_service: LibraryService, allowed_extensions=None):
        self._service = library_service
        self._allowed_extensions = allowed_extensions or DEFAULT_AUDIO_EXTENSIONS

    def _is_audio(self, path_str: str) -> bool:
        return Path(path_str).suffix.lower() in self._allowed_extensions

    def on_created(self, event):
        if not event.is_directory and self._is_audio(event.src_path):
            self._service.mark_present(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and self._is_audio(event.src_path):
            self._service.mark_missing(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            if self._is_audio(event.src_path):
                self._service.mark_missing(event.src_path)
            if self._is_audio(event.dest_path):
                self._service.mark_present(event.dest_path)


class DirectoryWatcher:
    """Gerencia a thread de monitoramento (Observer) do watchdog."""

    def __init__(self, directory: str, library_service: LibraryService):
        self.directory = str(Path(directory).resolve())
        self.handler = LibraryWatcherHandler(library_service)
        self._observer = Observer()

    def start(self):
        """Inicia o monitoramento em background (Thread separada)."""
        self._observer.schedule(self.handler, path=self.directory, recursive=True)
        self._observer.start()

    def stop(self):
        """Para o monitoramento e aguarda a encerramento da thread."""
        self._observer.stop()
        self._observer.join()