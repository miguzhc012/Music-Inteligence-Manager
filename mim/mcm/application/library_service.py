from typing import List

import hashlib

from mim.mcm.domain.library import LibraryEntry, FileStatus
from mim.mcm.domain.ports import LibraryEntryRepository


class LibraryService:
    """Serviço de aplicação para gerenciar a Library lógica."""

    def __init__(self, repo: LibraryEntryRepository):
        self._repo = repo

    def register_file(
        self,
        path: str,
        status: FileStatus = FileStatus.PRESENT,
    ) -> LibraryEntry:
        """Registra um arquivo conhecido ou atualiza seu status."""

        entry = self._repo.get_by_path(path)

        if entry:
            if entry.status != status:
                self._repo.update_status(entry.id, status)
                entry = LibraryEntry(entry.id, entry.path, status)

            return entry

        entry_id = hashlib.sha256(path.encode()).hexdigest()

        new_entry = LibraryEntry(
            entry_id,
            path,
            status,
        )

        self._repo.add(new_entry)

        return new_entry

    def mark_present(self, path: str) -> LibraryEntry:
        """Marca um arquivo como PRESENT."""

        return self.register_file(
            path,
            FileStatus.PRESENT,
        )

    def mark_missing(self, path: str) -> None:
        """Marca um arquivo como MISSING sem removê-lo da Library."""

        entry = self._repo.get_by_path(path)

        if entry and entry.status != FileStatus.MISSING:
            self._repo.update_status(
                entry.id,
                FileStatus.MISSING,
            )

    def get_entries(self) -> List[LibraryEntry]:
        """Retorna todos os arquivos registrados."""

        return self._repo.list_all()

# Extensões padrão de arquivos de áudio suportados
DEFAULT_AUDIO_EXTENSIONS = {
    ".mp3", ".flac", ".wav", ".m4a", ".ogg", ".aac", ".opus", ".wma"
}


class Scanner:
    """Autoridade de reconciliação da Library.

    Varre um diretório e atualiza os status dos arquivos conhecidos.
    Apenas arquivos com extensões permitidas são considerados.
    """

    def __init__(self, library_service: LibraryService, allowed_extensions: Optional[set] = None):
        self._service = library_service
        self._allowed_extensions = allowed_extensions or DEFAULT_AUDIO_EXTENSIONS

    """Autoridade de reconciliação da Library."""

    def __init__(self, library_service: LibraryService):
        self._service = library_service

    def scan_directory(self, directory: str) -> None:
        """Reconcilia a Library com o conteúdo atual do diretório."""

        from pathlib import Path

        dir_path = Path(directory).resolve()

        if not dir_path.is_dir():
            raise ValueError(
                f"Directory does not exist: {directory}"
            )

        found_paths = set()

        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                resolved = str(file_path.resolve())
                found_paths.add(resolved)

                self._service.mark_present(resolved)

        for entry in self._service.get_entries():
            if entry.path not in found_paths:
                self._service.mark_missing(entry.path)
