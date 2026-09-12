import sqlite3
from typing import Optional, List
from uuid import uuid4

from mim.mcm.domain.identity import Identity
from mim.mcm.domain.version import Version
from mim.mcm.domain.source import Source, SourceType
from mim.mcm.domain.release import Release, ReleaseTrack, ReleaseType
from mim.mcm.domain.resolution import Resolution, Evidence, EvidenceType
from mim.mcm.domain.library import LibraryEntry, FileStatus
from mim.mcm.domain.playback import QueueItem, PlaybackState, PlaybackPosition, PlaybackConfig, RepeatMode, ShuffleMode
from mim.mcm.domain.lyrics import Lyrics, LyricsLine, LyricsType, LyricsSource
from mim.mcm.domain.materialization import Materialization, MaterializationState, MaterializationQuality, DeviceStorage
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


class SQLiteQueueRepository:
    """Implementação SQLite do repositório de Queue."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def add(self, item: QueueItem) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO playback_queue (id, version_id, source_id, position, added_at) VALUES (?, ?, ?, ?, ?)",
            (item.id, item.version_id, item.source_id, item.position, item.added_at),
        )
        self._conn.commit()

    def get(self, item_id: str) -> Optional[QueueItem]:
        row = self._conn.execute(
            "SELECT id, version_id, source_id, position, added_at FROM playback_queue WHERE id = ?",
            (item_id,),
        ).fetchone()

        if row:
            return QueueItem(
                id=row["id"],
                version_id=row["version_id"],
                source_id=row["source_id"],
                position=row["position"],
                added_at=row["added_at"],
            )

        return None

    def get_queue(self) -> List[QueueItem]:
        rows = self._conn.execute(
            "SELECT id, version_id, source_id, position, added_at FROM playback_queue ORDER BY position"
        ).fetchall()

        return [
            QueueItem(
                id=row["id"],
                version_id=row["version_id"],
                source_id=row["source_id"],
                position=row["position"],
                added_at=row["added_at"],
            )
            for row in rows
        ]

    def remove(self, item_id: str) -> None:
        self._conn.execute(
            "DELETE FROM playback_queue WHERE id = ?",
            (item_id,),
        )
        self._conn.commit()

    def clear(self) -> None:
        self._conn.execute("DELETE FROM playback_queue")
        self._conn.commit()

    def reorder(self, item_id: str, new_position: int) -> None:
        """Move item to new position, shifting other items as needed."""
        # Get current position of the item
        row = self._conn.execute(
            "SELECT position FROM playback_queue WHERE id = ?",
            (item_id,),
        ).fetchone()
        
        if not row:
            return
        
        old_position = row["position"]
        
        if old_position == new_position:
            return
        
        if old_position < new_position:
            # Moving down: shift items between old+1 and new up by -1
            self._conn.execute(
                "UPDATE playback_queue SET position = position - 1 WHERE position > ? AND position <= ?",
                (old_position, new_position),
            )
        else:
            # Moving up: shift items between new and old-1 down by +1
            self._conn.execute(
                "UPDATE playback_queue SET position = position + 1 WHERE position >= ? AND position < ?",
                (new_position, old_position),
            )
        
        # Update the item's position
        self._conn.execute(
            "UPDATE playback_queue SET position = ? WHERE id = ?",
            (new_position, item_id),
        )
        self._conn.commit()


class SQLitePlaybackStateRepository:
    """Implementação SQLite do repositório de estado de playback."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get_state(self) -> PlaybackState:
        row = self._conn.execute(
            "SELECT value FROM playback_state WHERE key = 'state'"
        ).fetchone()

        if row:
            return PlaybackState(row["value"])

        return PlaybackState.STOPPED

    def set_state(self, state: PlaybackState) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO playback_state (key, value) VALUES ('state', ?)",
            (state.value,),
        )
        self._conn.commit()

    def get_position(self) -> PlaybackPosition:
        row = self._conn.execute(
            "SELECT value FROM playback_state WHERE key = 'position'"
        ).fetchone()

        if row:
            import json
            data = json.loads(row["value"])
            return PlaybackPosition(current_ms=data.get("current_ms", 0), duration_ms=data.get("duration_ms", 0))

        return PlaybackPosition()

    def set_position(self, position: PlaybackPosition) -> None:
        import json
        self._conn.execute(
            "INSERT OR REPLACE INTO playback_state (key, value) VALUES ('position', ?)",
            (json.dumps({"current_ms": position.current_ms, "duration_ms": position.duration_ms}),),
        )
        self._conn.commit()

    def get_config(self) -> PlaybackConfig:
        row = self._conn.execute(
            "SELECT value FROM playback_config WHERE key = 'config'"
        ).fetchone()

        if row:
            import json
            data = json.loads(row["value"])
            return PlaybackConfig(
                volume=data.get("volume", 1.0),
                repeat_mode=RepeatMode(data.get("repeat_mode", "off")),
                shuffle_mode=ShuffleMode(data.get("shuffle_mode", "off")),
                crossfade_ms=data.get("crossfade_ms", 0),
                gapless=data.get("gapless", True),
            )

        return PlaybackConfig()

    def set_config(self, config: PlaybackConfig) -> None:
        import json
        self._conn.execute(
            "INSERT OR REPLACE INTO playback_config (key, value) VALUES ('config', ?)",
            (json.dumps({
                "volume": config.volume,
                "repeat_mode": config.repeat_mode.value,
                "shuffle_mode": config.shuffle_mode.value,
                "crossfade_ms": config.crossfade_ms,
                "gapless": config.gapless,
            }),),
        )
        self._conn.commit()


class SQLiteLyricsRepository:
    """Implementação SQLite do repositório de letras."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get(self, version_id: str) -> Optional[Lyrics]:
        row = self._conn.execute(
            "SELECT version_id, lyrics_type, source, content, language, fetched_at FROM lyrics WHERE version_id = ?",
            (version_id,),
        ).fetchone()

        if not row:
            return None

        # Load synced lines
        lines = []
        if row["lyrics_type"] == "synced":
            line_rows = self._conn.execute(
                "SELECT timestamp_ms, text, translation, line_order FROM lyrics_lines WHERE version_id = ? ORDER BY line_order",
                (version_id,),
            ).fetchall()
            for lr in line_rows:
                lines.append(LyricsLine(
                    timestamp_ms=lr["timestamp_ms"],
                    text=lr["text"],
                    translation=lr["translation"],
                ))

        return Lyrics(
            version_id=row["version_id"],
            lyrics_type=LyricsType(row["lyrics_type"]),
            source=LyricsSource(row["source"]),
            content=row["content"],
            lines=lines,
            language=row["language"],
            fetched_at=row["fetched_at"],
        )

    def add(self, lyrics: Lyrics) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO lyrics (version_id, lyrics_type, source, content, language, fetched_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (lyrics.version_id, lyrics.lyrics_type.value, lyrics.source.value, lyrics.content, lyrics.language, lyrics.fetched_at),
        )
        # Delete existing lines
        self._conn.execute("DELETE FROM lyrics_lines WHERE version_id = ?", (lyrics.version_id,))
        # Insert new lines
        for idx, line in enumerate(lyrics.lines):
            self._conn.execute(
                "INSERT INTO lyrics_lines (id, version_id, timestamp_ms, text, translation, line_order) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid4()), lyrics.version_id, line.timestamp_ms, line.text, line.translation, idx),
            )
        self._conn.commit()

    def update(self, lyrics: Lyrics) -> None:
        self.add(lyrics)  # Upsert pattern

    def delete(self, version_id: str) -> None:
        self._conn.execute("DELETE FROM lyrics WHERE version_id = ?", (version_id,))
        self._conn.execute("DELETE FROM lyrics_lines WHERE version_id = ?", (version_id,))
        self._conn.commit()


class SQLiteMaterializationRepository:
    """Implementação SQLite do repositório de materializações."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get(self, source_id: str, device_id: str | None = None) -> Optional[Materialization]:
        if device_id:
            row = self._conn.execute(
                "SELECT id, source_id, device_id, state, file_path, quality, format, bitrate, sample_rate, bit_depth, file_size, checksum, created_at, updated_at FROM materializations WHERE source_id = ? AND device_id = ?",
                (source_id, device_id),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT id, source_id, device_id, state, file_path, quality, format, bitrate, sample_rate, bit_depth, file_size, checksum, created_at, updated_at FROM materializations WHERE source_id = ? ORDER BY CASE state WHEN 'downloaded' THEN 0 WHEN 'cached' THEN 1 ELSE 2 END LIMIT 1",
                (source_id,),
            ).fetchone()

        if not row:
            return None

        return Materialization(
            source_id=row["source_id"],
            state=MaterializationState(row["state"]),
            file_path=row["file_path"],
            device_id=row["device_id"],
            quality=MaterializationQuality(row["quality"]),
            format=row["format"],
            bitrate=row["bitrate"],
            sample_rate=row["sample_rate"],
            bit_depth=row["bit_depth"],
            file_size=row["file_size"],
            checksum=row["checksum"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def add(self, materialization: Materialization) -> None:
        mat_id = str(uuid4())
        self._conn.execute(
            "INSERT INTO materializations (id, source_id, device_id, state, file_path, quality, format, bitrate, sample_rate, bit_depth, file_size, checksum, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (mat_id, materialization.source_id, materialization.device_id, materialization.state.value, materialization.file_path, materialization.quality.value, materialization.format, materialization.bitrate, materialization.sample_rate, materialization.bit_depth, materialization.file_size, materialization.checksum),
        )
        self._conn.commit()

    def update(self, materialization: Materialization) -> None:
        self._conn.execute(
            "UPDATE materializations SET device_id = ?, state = ?, file_path = ?, quality = ?, format = ?, bitrate = ?, sample_rate = ?, bit_depth = ?, file_size = ?, checksum = ?, updated_at = CURRENT_TIMESTAMP WHERE source_id = ? AND device_id = ?",
            (materialization.device_id, materialization.state.value, materialization.file_path, materialization.quality.value, materialization.format, materialization.bitrate, materialization.sample_rate, materialization.bit_depth, materialization.file_size, materialization.checksum, materialization.source_id, materialization.device_id),
        )
        self._conn.commit()

    def delete(self, source_id: str, device_id: str | None = None) -> None:
        if device_id:
            self._conn.execute("DELETE FROM materializations WHERE source_id = ? AND device_id = ?", (source_id, device_id))
        else:
            self._conn.execute("DELETE FROM materializations WHERE source_id = ?", (source_id,))
        self._conn.commit()

    def get_by_device(self, device_id: str) -> List[Materialization]:
        rows = self._conn.execute(
            "SELECT id, source_id, device_id, state, file_path, quality, format, bitrate, sample_rate, bit_depth, file_size, checksum, created_at, updated_at FROM materializations WHERE device_id = ?",
            (device_id,),
        ).fetchall()

        return [
            Materialization(
                source_id=row["source_id"],
                state=MaterializationState(row["state"]),
                file_path=row["file_path"],
                device_id=row["device_id"],
                quality=MaterializationQuality(row["quality"]),
                format=row["format"],
                bitrate=row["bitrate"],
                sample_rate=row["sample_rate"],
                bit_depth=row["bit_depth"],
                file_size=row["file_size"],
                checksum=row["checksum"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def get_available_for_source(self, source_id: str) -> List[Materialization]:
        rows = self._conn.execute(
            "SELECT id, source_id, device_id, state, file_path, quality, format, bitrate, sample_rate, bit_depth, file_size, checksum, created_at, updated_at FROM materializations WHERE source_id = ? AND state IN ('cached', 'downloaded')",
            (source_id,),
        ).fetchall()

        return [
            Materialization(
                source_id=row["source_id"],
                state=MaterializationState(row["state"]),
                file_path=row["file_path"],
                device_id=row["device_id"],
                quality=MaterializationQuality(row["quality"]),
                format=row["format"],
                bitrate=row["bitrate"],
                sample_rate=row["sample_rate"],
                bit_depth=row["bit_depth"],
                file_size=row["file_size"],
                checksum=row["checksum"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]


class SQLiteDeviceStorageRepository:
    """Implementação SQLite do repositório de device storage."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get(self, device_id: str) -> Optional[DeviceStorage]:
        row = self._conn.execute(
            "SELECT device_id, total_bytes, free_bytes, path FROM device_storage WHERE device_id = ?",
            (device_id,),
        ).fetchone()

        if not row:
            return None

        return DeviceStorage(
            device_id=row["device_id"],
            total_bytes=row["total_bytes"],
            free_bytes=row["free_bytes"],
            path=row["path"],
        )

    def add(self, storage: DeviceStorage) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO device_storage (device_id, total_bytes, free_bytes, path, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (storage.device_id, storage.total_bytes, storage.free_bytes, storage.path),
        )
        self._conn.commit()

    def update(self, storage: DeviceStorage) -> None:
        self._conn.execute(
            "UPDATE device_storage SET total_bytes = ?, free_bytes = ?, path = ?, updated_at = CURRENT_TIMESTAMP WHERE device_id = ?",
            (storage.total_bytes, storage.free_bytes, storage.path, storage.device_id),
        )
        self._conn.commit()

    def delete(self, device_id: str) -> None:
        self._conn.execute("DELETE FROM device_storage WHERE device_id = ?", (device_id,))
        self._conn.commit()

    def list_all(self) -> List[DeviceStorage]:
        rows = self._conn.execute(
            "SELECT device_id, total_bytes, free_bytes, path FROM device_storage"
        ).fetchall()

        return [
            DeviceStorage(
                device_id=row["device_id"],
                total_bytes=row["total_bytes"],
                free_bytes=row["free_bytes"],
                path=row["path"],
            )
            for row in rows
        ]
