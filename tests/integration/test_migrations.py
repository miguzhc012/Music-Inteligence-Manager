import os
import tempfile
import pytest

from mim.mcm.infrastructure.sqlite_db import create_database

def test_database_migrations_applied():
    tmp_db = tempfile.NamedTemporaryFile(delete=False).name
    try:
        db = create_database(tmp_db)
        cursor = db._conn.cursor()
        
        # Check schema_version
        version = cursor.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        assert version == 4
        
        # Check tables existence
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = {row["name"] for row in tables}
        
        expected_tables = {
            "schema_version",
            "library_entries",
            "identities",
            "versions",
            "sources",
            "releases",
            "release_tracks",
            "resolutions",
            "resolution_evidence",
            "playback_queue",
            "playback_state",
            "playback_config",
        }
        
        assert expected_tables.issubset(table_names)
        db.close()
    finally:
        os.unlink(tmp_db)
