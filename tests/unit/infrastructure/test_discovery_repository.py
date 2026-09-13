import tempfile
import os
import pytest

from mim.mcm.infrastructure.sqlite_db import create_database
from mim.mcm.infrastructure.repositories import (
    SQLiteDiscoveryRepository,
    SQLiteAcousticProfileRepository,
    SQLiteRecommendationRepository,
    SQLiteUserTasteProfileRepository,
    SQLiteAudioFeatureRepository,
)
from mim.mcm.domain.discovery import SearchMatch, DiscoveryMethod, MatchQuality, AcousticProfile
from mim.mcm.domain.recommendation import Recommendation, RecommendationType, SimilarityAlgorithm, UserTasteProfile, AudioFeature


@pytest.fixture
def discovery_setup():
    tmp_db = tempfile.NamedTemporaryFile(delete=False).name
    db = create_database(tmp_db)
    conn = db._conn
    
    discovery_repo = SQLiteDiscoveryRepository(conn)
    acoustic_repo = SQLiteAcousticProfileRepository(conn)
    recommendation_repo = SQLiteRecommendationRepository(conn)
    taste_repo = SQLiteUserTasteProfileRepository(conn)
    audio_feature_repo = SQLiteAudioFeatureRepository(conn)
    
    yield {
        "db": db,
        "discovery_repo": discovery_repo,
        "acoustic_repo": acoustic_repo,
        "recommendation_repo": recommendation_repo,
        "taste_repo": taste_repo,
        "audio_feature_repo": audio_feature_repo,
    }
    
    db.close()
    os.unlink(tmp_db)


def test_discovery_domain_entities():
    """Testa entidades de domínio de discovery."""
    match = SearchMatch(
        id="m1",
        identity_id="id1",
        title="Bohemian Rhapsody",
        artist="Queen",
        version_id="v1",
        source_id="s1",
        album="A Night at the Opera",
        quality=MatchQuality.HIGH,
        score=0.95,
        method=DiscoveryMethod.TITLE_MATCH,
    )
    
    assert match.identity_id == "id1"
    assert match.quality == MatchQuality.HIGH
    assert match.score == 0.95
    
    profile = AcousticProfile(
        version_id="v1",
        tempo_bpm=144.0,
        key="Bb",
        mode="minor",
        duration_ms=354000,
        energy=0.427,
        danceability=0.604,
        valence=0.369,
    )
    
    assert profile.version_id == "v1"
    assert profile.tempo_bpm == 144.0
    assert profile.key == "Bb"


def test_search_match_repository(discovery_setup):
    repo = discovery_setup["discovery_repo"]
    
    match = SearchMatch(
        id="m1",
        identity_id="id1",
        title="Test Song",
        artist="Test Artist",
        version_id="v1",
        source_id="s1",
        quality=MatchQuality.EXACT,
        score=0.95,
        method=DiscoveryMethod.TITLE_MATCH,
    )
    
    repo.save_match(match)
    
    # Get by identity
    matches = repo.get_matches("id1")
    assert len(matches) == 1
    assert matches[0].title == "Test Song"
    
    # Get by version
    by_version = repo.get_by_version("v1")
    assert len(by_version) == 1
    assert by_version[0].score == 0.95
    
    # Get best match
    best = repo.get_best_match("id1")
    assert best is not None
    assert best.id == "m1"
    
    # No match for non-existent
    no_match = repo.get_best_match("nonexistent")
    assert no_match is None


def test_acoustic_profile_repository(discovery_setup):
    repo = discovery_setup["acoustic_repo"]
    
    profile = AcousticProfile(
        version_id="v1",
        tempo_bpm=120.0,
        key="C",
        mode="major",
        energy=0.8,
        danceability=0.7,
        valence=0.9,
    )
    
    repo.add(profile)
    
    # Get
    fetched = repo.get("v1")
    assert fetched is not None
    assert fetched.tempo_bpm == 120.0
    assert fetched.energy == 0.8
    
    # Update
    updated = AcousticProfile(
        version_id="v1",
        tempo_bpm=125.0,
        key="C",
        mode="major",
        energy=0.85,
        danceability=0.75,
        valence=0.95,
    )
    repo.update(updated)
    
    fetched = repo.get("v1")
    assert fetched.tempo_bpm == 125.0
    
    # Find similar
    similar = repo.find_similar(profile)
    assert len(similar) == 0  # Only one in DB
    
    # Delete
    repo.delete("v1")
    assert repo.get("v1") is None


def test_recommendation_repository(discovery_setup):
    repo = discovery_setup["recommendation_repo"]
    
    rec = Recommendation(
        source_version_id="v1",
        target_identity_id="id1",
        target_version_id="v2",
        type=RecommendationType.SIMILAR_TRACKS,
        algorithm=SimilarityAlgorithm.COSINE_SIMILARITY,
        similarity_score=0.85,
        confidence=0.9,
    )
    
    repo.add(rec)
    
    # Get by source
    by_source = repo.get_by_source("v1")
    assert len(by_source) == 1
    assert by_source[0].similarity_score == 0.85
    
    # Get recent
    recent = repo.get_recent()
    assert len(recent) == 1
    
    # Delete
    repo.delete(rec.id)
    assert repo.get_recent() == []


def test_user_taste_profile_repository(discovery_setup):
    repo = discovery_setup["taste_repo"]
    
    profile = UserTasteProfile(
        user_id="user1",
        favorite_artists=["Queen", "The Beatles"],
        favorite_genres=["Rock", "Pop"],
        listening_count=100,
        total_ms_listened=3600000,
        skip_rate=0.1,
        repeat_rate=0.3,
    )
    
    repo.add(profile)
    
    # Get
    fetched = repo.get("user1")
    assert fetched is not None
    assert "Queen" in fetched.favorite_artists
    assert fetched.listening_count == 100
    
    # Update
    updated = UserTasteProfile(
        user_id="user1",
        favorite_artists=["Queen", "The Beatles", "Led Zeppelin"],
        favorite_genres=["Rock"],
        listening_count=150,
        total_ms_listened=5400000,
        skip_rate=0.05,
        repeat_rate=0.25,
    )
    repo.update(updated)
    
    fetched = repo.get("user1")
    assert fetched.listening_count == 150
    assert "Led Zeppelin" in fetched.favorite_artists
    
    # List all
    all_profiles = repo.list_all()
    assert len(all_profiles) == 1
    
    # Delete
    repo.delete("user1")
    assert repo.get("user1") is None


def test_audio_feature_repository(discovery_setup):
    repo = discovery_setup["audio_feature_repo"]
    
    feature = AudioFeature(
        version_id="v1",
        tempo_bpm=120.0,
        key="C",
        mode="major",
        energy=0.8,
        danceability=0.7,
        valence=0.9,
        acousticness=0.1,
        instrumentalness=0.0,
        liveness=0.1,
        speechiness=0.05,
        duration_ms=180000,
    )
    
    repo.add(feature)
    
    # Get
    fetched = repo.get("v1")
    assert fetched is not None
    assert fetched.energy == 0.8
    assert fetched.valence == 0.9
    
    # Find similar
    similar = repo.find_similar(feature)
    assert len(similar) == 0  # Only one in DB
    
    # Delete
    repo.delete("v1")
    assert repo.get("v1") is None
