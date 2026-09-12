import sqlite3
from pathlib import Path
from uuid import uuid4

from mim.mcm.domain.resolution import Resolution, Evidence, EvidenceType
from mim.mcm.domain.confidence import Confidence
from mim.mcm.domain.availability import Availability, AvailabilityStatus


def up(db_path: str) -> None:
    """Migração para adicionar tabelas de Resolution e evidências."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    # Cria tabela resolutions
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS resolutions (
            resolution_id TEXT PRIMARY KEY,
            version_id TEXT NOT NULL,
            source_id TEXT,
            confidence_value REAL NOT NULL,
            availability_status TEXT NOT NULL CHECK (availability_status IN ('unknown', 'available', 'unavailable', 'stale')),
            resolved_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (version_id) REFERENCES versions(id)
        )
    )

    # Cria tabela de evidências
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS resolution_evidence (
            id TEXT PRIMARY KEY,
            resolution_id TEXT NOT NULL,
            evidence_type TEXT NOT NULL CHECK (evidence_type IN ('metadata_match', 'acoustic_fingerprint', 'isrc_match', 'mbid_match', 'file_hash', 'user_confirmation', 'provider_assertion')),
            weight REAL NOT NULL,
            description TEXT,
            source_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (resolution_id) REFERENCES resolutions(resolution_id)
        )
    )

    db.commit()
    db.close()


def down(db_path: str) -> None:
    """Desfaz a migração (DROP tables)."""
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("DROP TABLE IF EXISTS resolution_evidence")
    cursor.execute("DROP TABLE IF EXISTS resolutions")
    db.commit()
    db.close()
