from mim.mcm.application.metadata_pipeline import (
    MetadataPipeline,
    PipelineConfig,
    PipelineResult,
    PipelineStep,
)
from mim.mcm.domain.audio_metadata import AudioExtractionService, AudioMetadata, AudioCodec, ModeEnum
from mim.mcm.application.audio_extraction import AudioExtractionApplicationService
from mim.mcm.application.identity_resolution import IdentityResolutionApplicationService
from mim.mcm.domain.version import Version
from mim.mcm.domain.version_policy import VersionPolicyEngine

import asyncio
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_audio_service():
    service = Mock(spec=AudioExtractionApplicationService)
    metadata = AudioMetadata(
        path="/test/file.mp3",
        codec=AudioCodec.MP3,
        duration_ms=180000,
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        isrc="ISRC123",
        musicbrainz_track_id="MBID123",
        acoustid_id="ACUSTID123",
        bpm=120,
        key_name="C",
        mode_enum=ModeEnum.MAJOR,
        replay_gain=0.0,
    )
    service.extract.return_value = metadata
    service.get_file_hash.return_value = "abc123"
    return service

@pytest.fixture
def mock_identity_service():
    service = Mock(spec=IdentityResolutionApplicationService)
    result = Mock()
    result.is_resolved.return_value = True
    result.resolved_identity_id = "id123"
    result.resolved_version_id = "ver123"
    result.confidence = 0.8
    service.resolve_and_enrich.return_value = result
    return service

@pytest.fixture
def mock_version_engine():
    engine = Mock(spec=VersionPolicyEngine)
    version = Mock(spec=Version)
    version.id = "ver123"
    version.name = "Version 1"
    version.label = "Acoustic"
    engine.select_version.return_value = version
    engine.get_rationale.return_value = "Rationale"
    return engine

@pytest.fixture
def pipeline_config():
    return PipelineConfig(
        timeout_seconds=5.0,
        max_retries=1,
        enable_fingerprint=False,
        enable_musicbrainz=False,
        enable_isrc=False,
        enable_identity_resolution=True,
        enable_materialization_link=False,
        enable_acoustic_analysis=False,
        enable_recommendation=False,
        idempotency_key="test_key",
    )

@pytest.fixture
def full_pipeline(pipeline_config):
    return MetadataPipeline(config=pipeline_config)


def test_pipeline_initialization(full_pipeline):
    """Testa inicialização do pipeline com etapas padrão."""
    assert full_pipeline.config.timeout_seconds == 5.0
    assert len(full_pipeline._stages) == 3  # Apenas etapas obrigatórias (fingerprint desabilitado)
    assert full_pipeline._stages[0].step == PipelineStep.AUDIO_EXTRACTION
    assert full_pipeline._stages[1].step == PipelineStep.TAG_NORMALIZATION
    assert full_pipeline._stages[2].step == PipelineStep.IDENTITY_RESOLUTION


def test_pipeline_run_success(mock_audio_service, mock_identity_service, mock_version_engine, pipeline_config):
    """Testa execução completa com sucesso."""
    pipeline = MetadataPipeline(config=pipeline_config)
    result = asyncio.run(pipeline.run("/test/file.mp3", mock_audio_service, mock_identity_service, mock_version_engine))
    assert result.success is True
    assert result.audio_metadata is not None
    assert result.identity_resolution is not None
    assert result.stages[0]["step"] == PipelineStep.AUDIO_EXTRACTION.value
    assert result.stages[1]["step"] == PipelineStep.TAG_NORMALIZATION.value
    assert result.stages[2]["step"] == PipelineStep.IDENTITY_RESOLUTION.value
    assert result.total_duration_ms > 0


def test_pipeline_error_handling(mock_audio_service, mock_identity_service, mock_version_engine, pipeline_config):
    """Testa tratamento de erros em etapas obrigatórias."""
    # Forçar falha na extração de áudio
    def failing_extract(*args, **kwargs):
        raise Exception("Extract failed")
    mock_audio_service.extract.side_effect = failing_extract
    
    pipeline = MetadataPipeline(config=pipeline_config)
    result = asyncio.run(pipeline.run("/test/file.mp3", mock_audio_service, mock_identity_service, mock_version_engine))
    assert result.success is False
    assert len(result.errors) > 0
    assert result.errors[0]["success"] is False
    assert result.errors[0]["step"] == PipelineStep.AUDIO_EXTRACTION.value


def test_pipeline_idempotency(mock_audio_service, mock_identity_service, mock_version_engine, pipeline_config):
    """Testa comportamento idempotente com chave repetida."""
    pipeline = MetadataPipeline(config=pipeline_config)
    # Primeira execução
    result1 = asyncio.run(pipeline.run("/test/file.mp3", mock_audio_service, mock_identity_service, mock_version_engine))
    # Segunda execução com mesmo idempotency_key
    result2 = asyncio.run(pipeline.run("/test/file.mp3", mock_audio_service, mock_identity_service, mock_version_engine))
    assert result1.success == result2.success
    assert result1.audio_metadata == result2.audio_metadata


def test_pipeline_metrics(mock_audio_service, mock_identity_service, mock_version_engine, pipeline_config):
    """Testa atualização de métricas do pipeline."""
    pipeline = MetadataPipeline(config=pipeline_config)
    asyncio.run(pipeline.run("/test/file.mp3", mock_audio_service, mock_identity_service, mock_version_engine))
    metrics = pipeline.get_metrics()
    assert metrics["total_runs"] == 1
    assert metrics["successful_runs"] == 1
    assert metrics["average_duration_ms"] > 0
    assert "audio_extraction" in metrics["stage_stats"]


def test_pipeline_optional_stages(mock_audio_service, mock_identity_service, mock_version_engine):
    """Testa que etapas opcionais são adicionadas/removidas via config."""
    config = PipelineConfig(
        enable_fingerprint=True,
        enable_musicbrainz=True,
        enable_isrc=False,
        enable_materialization_link=False,
        enable_acoustic_analysis=False,
        enable_recommendation=False,
    )
    pipeline = MetadataPipeline(config=config)
    assert len(pipeline._stages) == 5  # Três obrigatórias + duas opcionais
    assert PipelineStep.FINGERPRINT_GENERATION in [s.step for s in pipeline._stages]
    assert PipelineStep.MUSICBRAINZ_ENRICHMENT in [s.step for s in pipeline._stages]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])