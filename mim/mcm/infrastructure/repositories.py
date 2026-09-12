import sqlite3
from typing import Optional, List
from uuid import uuid4

from mim.mcm.domain.identity import Identity
from mim.mcm.domain.version import Version
from mim.mcm.domain.source import Source, SourceType
from mim.mcm.domain.release import Release, ReleaseTrack, ReleaseType
from mim.mcm.domain.resolution import Resolution, Evidence, EvidenceType
from mim.mcm.domain.library import LibraryEntry, FileStatus
from mim.mcm.domain.ports import (
    IdentityRepository,
    VersionRepository,
    SourceRepository,
    ReleaseRepository,
    ResolutionRepository,
    LibraryEntryRepository,
)
from mim.mcm.domain.confidence import Confidence
from mim.mcm.domain.availability import Availability, AvailabilityStatus


class SQLiteIdentityRepository(IdentityRepository):
    """Implementação SQLite do repositório de Identity."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def add(self, identity: Identity) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO identities (id, title, artist) VALUES (?, ?, ?)",
            (identity.id, identity.title, identity.artist),
        )
        self._conn.commit()

    def get(self, identity_id: str) -> Optional[Identity]:
        row = self._conn.execute(
            "SELECT id, title, artist FROM identities WHERE id = ?",
            (identity_id,),
        ).fetchone()

        if row:
            return Identity(id=row["id"], title=row["title"], artist=row["artist"])

        return None


class SQLiteVersionRepository(VersionRepository):
    """Implementação SQLite do repositório de Version."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def add(self, version: Version) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO versions (id, identity_id, label) VALUES (?, ?, ?)",
            (version.id, version.identity_id, version.label),
        )
        self._conn.commit()

    def get(self, version_id: str) -> Optional[Version]:
        row = self._conn.execute(
            "SELECT id, identity_id, label FROM versions WHERE id = ?",
            (version_id,),
        ).fetchone()

        if row:
            return Version(
                id=row["id"],
                identity_id=row["identity_id"],
                label=row["label"],
            )

        return None


class SQLiteSourceRepository(SourceRepository):
    """Implementação SQLite do repositório de Source."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def add(self, source: Source) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO sources (id, version_id, source_type) VALUES (?, ?, ?)",
            (source.id, source.version_id, source.source_type.value),
        )
        self._conn.commit()

    def get(self, source_id: str) -> Optional[Source]:
        row = self._conn.execute(
            "SELECT id, version_id, source_type FROM sources WHERE id = ?",
            (source_id,),
        ).fetchone()

        if row:
            return Source(
                id=row["id"],
                version_id=row["version_id"],
                source_type=SourceType(row["source_type"]),
            )

        return None

    def get_by_version(self, version_id: str) -> List[Source]:
        rows = self._conn.execute(
            "SELECT id, version_id, source_type FROM sources WHERE version_id = ?",
            (version_id,),
        ).fetchall()

        return [
            Source(
                id=row["id"],
                version_id=row["version_id"],
                source_type=SourceType(row["source_type"]),
            )
            for row in rows
        ]


class SQLiteLibraryEntryRepository(LibraryEntryRepository):
    """Implementação SQLite do repositório de LibraryEntry."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def add(self, entry: LibraryEntry) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO library_entries (id, path, status) "
            "VALUES (?, ?, ?)",
            (entry.id, entry.path, entry.status.value),
        )
        self._conn.commit()

    def get_by_id(self, entry_id: str) -> Optional[LibraryEntry]:
        row = self._conn.execute(
            "SELECT id, path, status "
            "FROM library_entries WHERE id = ?",
            (entry_id,),
        ).fetchone()

        if row:
            return LibraryEntry(
                row["id"],
                row["path"],
                FileStatus(row["status"]),
            )

        return None

    def get_by_path(self, path: str) -> Optional[LibraryEntry]:
        row = self._conn.execute(
            "SELECT id, path, status "
            "FROM library_entries WHERE path = ?",
            (path,),
        ).fetchone()

        if row:
            return LibraryEntry(
                row["id"],
                row["path"],
                FileStatus(row["status"]),
            )

        return None

    def update_status(
        self,
        entry_id: str,
        status: FileStatus,
    ) -> None:
        self._conn.execute(
            "UPDATE library_entries SET status = ? WHERE id = ?",
            (status.value, entry_id),
        )
        self._conn.commit()

    def list_all(self) -> list[LibraryEntry]:
        rows = self._conn.execute(
            "SELECT id, path, status FROM library_entries"
        ).fetchall()

        return [
            LibraryEntry(
                row["id"],
                row["path"],
                FileStatus(row["status"]),
            )
            for row in rows
        ]


class SQLiteReleaseRepository(ReleaseRepository):
    """Implementação SQLite para Release e ReleaseTrack."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get_release(self, release_id: str) -> Optional[Release]:
        cursor = self._conn.execute(
            "SELECT id, identity_id, title, release_type, release_date, label, catalog_number, cover_url "
            "FROM releases WHERE id = ?",
            (release_id,)
        ).fetchone()
        if not cursor:
            return None
        return Release(
            id=cursor["id"],
            identity_id=cursor["identity_id"],
            title=cursor["title"],
            release_type=ReleaseType(cursor["release_type"].lower()),
            release_date=cursor["release_date"],
            label=cursor["label"],
            catalog_number=cursor["catalog_number"],
            cover_url=cursor["cover_url"],
        )

    def add_release(self, release: Release) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO releases (id, identity_id, title, release_type, release_date, label, catalog_number, cover_url) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                release.id,
                release.identity_id,
                release.title,
                release.release_type.value,
                release.release_date,
                release.label,
                release.catalog_number,
                release.cover_url,
            ),
        )
        self._conn.commit()

    def get_tracks_by_release(self, release_id: str) -> list[ReleaseTrack]:
        cursor = self._conn.execute(
            "SELECT id, release_id, version_id, track_number, disc_number, duration_ms, isrc, explicit "
            "FROM release_tracks WHERE release_id = ?",
            (release_id,)
        ).fetchall()
        return [
            ReleaseTrack(
                id=row["id"],
                release_id=row["release_id"],
                version_id=row["version_id"],
                track_number=row["track_number"],
                disc_number=row["disc_number"],
                duration_ms=row["duration_ms"],
                isrc=row["isrc"],
                explicit=bool(row["explicit"]),
            )
            for row in cursor
        ]

    def add_track(self, track: ReleaseTrack) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO release_tracks (id, release_id, version_id, track_number, disc_number, duration_ms, isrc, explicit) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                track.id,
                track.release_id,
                track.version_id,
                track.track_number,
                track.disc_number,
                track.duration_ms,
                track.isrc,
                int(track.explicit),
            ),
        )
        self._conn.commit()

    def get_releases_by_identity(self, identity_id: str) -> list[Release]:
        cursor = self._conn.execute(
            "SELECT id, identity_id, title, release_type, release_date, label, catalog_number, cover_url "
            "FROM releases WHERE identity_id = ?",
            (identity_id,)
        ).fetchall()
        return [
            Release(
                id=row["id"],
                identity_id=row["identity_id"],
                title=row["title"],
                release_type=ReleaseType(row["release_type"].lower()),
                release_date=row["release_date"],
                label=row["label"],
                catalog_number=row["catalog_number"],
                cover_url=row["cover_url"],
            )
            for row in cursor
        ]


class SQLiteResolutionRepository(ResolutionRepository):
    """Implementação SQLite para resoluções de Version -> Source."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get(self, resolution_id: str) -> Optional[Resolution]:
        cursor = self._conn.execute(
            "SELECT resolution_id, version_id, source_id, confidence_value, availability_status, resolved_at "
            "FROM resolutions WHERE resolution_id = ?",
            (resolution_id,)
        ).fetchone()
        if not cursor:
            return None
        res = Resolution(
            resolution_id=cursor["resolution_id"],
            version_id=cursor["version_id"],
            source_id=cursor["source_id"],
        )
        res.confidence = Confidence(cursor["confidence_value"])
        res.availability = Availability(AvailabilityStatus(cursor["availability_status"]))
        res.resolved_at = cursor["resolved_at"]
        # Load evidence
        evidence_cursor = self._conn.execute(
            "SELECT evidence_type, weight, description, source_id FROM resolution_evidence WHERE resolution_id = ?",
            (resolution_id,)
        ).fetchall()
        for row in evidence_cursor:
            res.evidence.append(
                Evidence(
                    type=EvidenceType(row["evidence_type"]),
                    weight=row["weight"],
                    description=row["description"],
                    source_id=row["source_id"],
                )
            )
        return res

    def get_by_version(self, version_id: str) -> Optional[Resolution]:
        cursor = self._conn.execute(
            "SELECT resolution_id, version_id, source_id, confidence_value, availability_status, resolved_at "
            "FROM resolutions WHERE version_id = ?",
            (version_id,)
        ).fetchone()
        if not cursor:
            return None
        res = Resolution(
            resolution_id=cursor["resolution_id"],
            version_id=cursor["version_id"],
            source_id=cursor["source_id"],
        )
        res.confidence = Confidence(cursor["confidence_value"])
        res.availability = Availability(AvailabilityStatus(cursor["availability_status"]))
        res.resolved_at = cursor["resolved_at"]
        # Load evidence
        evidence_cursor = self._conn.execute(
            "SELECT evidence_type, weight, description, source_id FROM resolution_evidence WHERE resolution_id = ?",
            (cursor["resolution_id"],)
        ).fetchall()
        for row in evidence_cursor:
            res.evidence.append(
                Evidence(
                    type=EvidenceType(row["evidence_type"]),
                    weight=row["weight"],
                    description=row["description"],
                    source_id=row["source_id"],
                )
            )
        return res

    def add(self, resolution: Resolution) -> None:
        # Insert or replace resolution
        self._conn.execute(
            "INSERT OR REPLACE INTO resolutions (resolution_id, version_id, source_id, confidence_value, availability_status, resolved_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                resolution.resolution_id,
                resolution.version_id,
                resolution.source_id,
                resolution.confidence.value,
                resolution.availability.status.value,
                resolution.resolved_at,
            ),
        )
        # Delete existing evidence for this resolution
        self._conn.execute(
            "DELETE FROM resolution_evidence WHERE resolution_id = ?",
            (resolution.resolution_id,)
        )
        # Insert new evidence
        for evidence in resolution.evidence:
            self._conn.execute(
                "INSERT INTO resolution_evidence (id, resolution_id, evidence_type, weight, description, source_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(uuid4()),
                    resolution.resolution_id,
                    evidence.type.value,
                    evidence.weight,
                    evidence.description,
                    evidence.source_id,
                ),
            )
        self._conn.commit()

    def update(self, resolution: Resolution) -> None:
        """Update existing resolution, preserving evidence unless explicitly deleted."""
        if not self._conn.execute(
            "SELECT 1 FROM resolutions WHERE resolution_id = ?",
            (resolution.resolution_id,)
        ).fetchone():
            raise ValueError(f"Resolution {resolution.resolution_id} not found")
        # Update main resolution record (source_id, confidence, availability, resolved_at)
        self._conn.execute(
            "UPDATE resolutions SET source_id = ?, confidence_value = ?, availability_status = ?, resolved_at = ? "
            "WHERE resolution_id = ?",
            (
                resolution.source_id,
                resolution.confidence.value,
                resolution.availability.status.value,
                resolution.resolved_at,
                resolution.resolution_id,
            ),
        )
        # If evidence list is empty, clear existing evidence
        if not resolution.evidence:
            self._conn.execute(
                "DELETE FROM resolution_evidence WHERE resolution_id = ?",
                (resolution.resolution_id,)
            )
        else:
            # Replace evidence: delete old, insert new
            self._conn.execute(
                "DELETE FROM resolution_evidence WHERE resolution_id = ?",
                (resolution.resolution_id,)
            )
            for evidence in resolution.evidence:
                self._conn.execute(
                    "INSERT INTO resolution_evidence (id, resolution_id, evidence_type, weight, description, source_id) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid4()),
                        resolution.resolution_id,
                        evidence.type.value,
                        evidence.weight,
                        evidence.description,
                        evidence.source_id,
                    ),
                )
        self._conn.commit()
