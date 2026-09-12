import sqlite3
from pathlib import Path
from typing import Optional

from mim.mcm.domain.release import Release, ReleaseTrack, ReleaseType
from mim.mcm.domain.ports import ReleaseRepository


class SQLiteDatabase:
    """Gerenciador de conexão e migrações para SQLite."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._enable_foreign_keys()
        self._run_migrations()
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def _enable_foreign_keys(self) -> None:
        assert self._conn is not None
        self._conn.execute("PRAGMA foreign_keys = ON")

    def _run_migrations(self) -> None:
        assert self._conn is not None

        cursor = self._conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        current = cursor.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()[0] or 0

        migrations = [
            (
                1,
                """
                CREATE TABLE IF NOT EXISTS library_entries (
                    id TEXT PRIMARY KEY,
                    path TEXT UNIQUE NOT NULL,
                    status TEXT NOT NULL
                        CHECK (status IN ('PRESENT', 'MISSING'))
                )
                """,
            ),
        ]

        for version, sql in migrations:
            if version > current:
                cursor.execute(sql)
                cursor.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (version,),
                )

        self._conn.commit()


class SQLiteReleaseRepository(ReleaseRepository):
    """Implementação SQLite para Release e ReleaseTrack."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def _ensure_tables(self) -> None:
        cursor = self._conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS releases (
                id TEXT PRIMARY KEY,
                identity_id TEXT NOT NULL,
                title TEXT NOT NULL,
                release_type TEXT NOT NULL CHECK (release_type IN ('album', 'single', 'ep', 'compilation', 'soundtrack', 'live', 'remix', 'other')),
                release_date TEXT NOT NULL,
                label TEXT,
                catalog_number TEXT,
                cover_url TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS release_tracks (
                id TEXT PRIMARY KEY,
                release_id TEXT NOT NULL,
                version_id TEXT NOT NULL,
                track_number INTEGER NOT NULL,
                disc_number INTEGER NOT NULL DEFAULT 1,
                duration_ms INTEGER,
                isrc TEXT,
                explicit INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (release_id) REFERENCES releases(id)
            )
            """
        )
        self._conn.commit()

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


def create_database(db_path: str) -> SQLiteDatabase:
    db = SQLiteDatabase(db_path)
    db.connect()
    return db