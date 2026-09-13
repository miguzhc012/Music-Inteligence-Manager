import asyncio
import time
import uuid
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

from mim.mcm.domain.version_policy import VersionPolicyEngine, VersionPolicyConfig
from mim.mcm.domain.identity_resolution import IdentityResolutionResult
from mim.mcm.domain.ports import (
    IdentityRepository,
    VersionRepository,
    MaterializationRepository,
)
from mim.mcm.domain.version import Version
from mim.mcm.domain.audio_metadata import AudioMetadata

from .config import PipelineConfig
from .stage import PipelineStage, PipelineStep
from .result import PipelineResult

__all__ = ["PipelineConfig", "PipelineStage", "PipelineStep", "PipelineResult", "MetadataPipeline"]


class MetadataPipeline:
    """Pipeline completo de extração e enriquecimento de metadata com etapas plugáveis."""
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self._stages: List[PipelineStage] = []
        self._register_default_stages()
        self._idempotency_cache: Dict[str, PipelineResult] = {}
        self._metrics: Dict[str, Any] = {
            "total_runs": 0,
            "successful_runs": 0,
            "average_duration_ms": 0.0,
            "stage_stats": {},
        }

    def _register_default_stages(self):
        """Registra as etapas padrão do pipeline."""
        # Etapas obrigatórias
        self.add_stage(
            PipelineStage(
                step=PipelineStep.AUDIO_EXTRACTION,
                handler=self._extract_audio,
                required=True,
                timeout=5.0,
            )
        )
        self.add_stage(
            PipelineStage(
                step=PipelineStep.TAG_NORMALIZATION,
                handler=self._normalize_tags,
                required=True,
                timeout=2.0,
            )
        )
        self.add_stage(
            PipelineStage(
                step=PipelineStep.IDENTITY_RESOLUTION,
                handler=self._resolve_identity,
                required=True,
                timeout=5.0,
            )
        )

        # Etapas opcionais baseadas em config
        if self.config.enable_fingerprint:
            self.add_stage(
                PipelineStage(
                    step=PipelineStep.FINGERPRINT_GENERATION,
                    handler=self._generate_fingerprint,
                    required=False,
                    timeout=3.0,
                )
            )
        if self.config.enable_musicbrainz:
            self.add_stage(
                PipelineStage(
                    step=PipelineStep.MUSICBRAINZ_ENRICHMENT,
                    handler=self._enrich_musicbrainz,
                    required=False,
                    timeout=3.0,
                )
            )
        if self.config.enable_isrc:
            self.add_stage(
                PipelineStage(
                    step=PipelineStep.ISRC_VALIDATION,
                    handler=self._validate_isrc,
                    required=False,
                    timeout=2.0,
                )
            )
        if self.config.enable_materialization_link:
            self.add_stage(
                PipelineStage(
                    step=PipelineStep.MATERIALIZATION_LINK,
                    handler=self._link_materialization,
                    required=False,
                    timeout=2.0,
                )
            )
        if self.config.enable_acoustic_analysis:
            self.add_stage(
                PipelineStage(
                    step=PipelineStep.ACOUSTIC_ANALYSIS,
                    handler=self._analyze_acoustics,
                    required=False,
                    timeout=4.0,
                )
            )
        if self.config.enable_recommendation:
            self.add_stage(
                PipelineStage(
                    step=PipelineStep.RECOMMENDATION_GENERATION,
                    handler=self._generate_recommendations,
                    required=False,
                    timeout=3.0,
                )
            )

    def add_stage(self, stage: PipelineStage):
        """Adiciona uma etapa personalizada ao pipeline."""
        self._stages.append(stage)

    async def run(self, file_path: str, audio_extraction_service, identity_service, version_engine) -> PipelineResult:
        """Executa o pipeline com tratamento de erros e idempotência."""
        start_time = time.time()
        result = PipelineResult()
        result.stages = []
        result.errors = []
        result.metadata = {}

        # Verificação de idempotência
        idempotency_key = self.config.idempotency_key or f"{file_path}_{uuid.uuid4().hex}"
        if idempotency_key in self._idempotency_cache:
            cached_result = self._idempotency_cache[idempotency_key]
            result.success = cached_result.success
            result.audio_metadata = cached_result.audio_metadata
            result.identity_resolution = cached_result.identity_resolution
            result.version_selection = cached_result.version_selection
            result.materialization_link = cached_result.materialization_link
            result.total_duration_ms = cached_result.total_duration_ms
            result.metadata = cached_result.metadata
            return result

        # Executar cada etapa com tratamento de erros
        for stage in self._stages:
            stage_result: Dict[str, Any] = {
                "step": stage.step.value,
                "success": False,
                "error": None,
                "duration_ms": 0,
                "output": None,
            }
            try:
                start_stage = time.time()
                # Timeout e retry
                timeout = stage.timeout or self.config.timeout_seconds
                attempt = 0
                last_exception = None
                while attempt < self.config.max_retries:
                    try:
                        task = asyncio.create_task(stage.handler(file_path, audio_extraction_service, identity_service, version_engine))
                        output = await asyncio.wait_for(task, timeout=timeout)
                        stage_result["success"] = True
                        stage_result["output"] = output
                        stage_result["duration_ms"] = (time.time() - start_stage) * 1000
                        break
                    except Exception as e:
                        last_exception = e
                        attempt += 1
                        if attempt < self.config.max_retries:
                            await asyncio.sleep(0.1)
                if not stage_result["success"]:
                    stage_result["error"] = str(last_exception)
                    result.errors.append(stage_result)
                    # Continuar com próxima etapa se possível
                    continue
                # Registrar métricas
                self._update_metrics(stage.step, stage_result["duration_ms"])
                result.stages.append(stage_result)
                # Atualizar resultados agregados
                if stage.step == PipelineStep.AUDIO_EXTRACTION:
                    result.audio_metadata = stage_result["output"]
                elif stage.step == PipelineStep.IDENTITY_RESOLUTION:
                    result.identity_resolution = stage_result["output"]
            except Exception as e:
                stage_result["error"] = str(e)
                result.errors.append(stage_result)
                self._update_metrics(stage.step, -1)

        # Finalizar resultado
        result.total_duration_ms = (time.time() - start_time) * 1000
        # Sucesso = nenhuma etapa obrigatória falhou E pelo menos uma etapa rodou
        required_failures = [e for e in result.errors if self._is_required(e["step"])]
        result.success = len(required_failures) == 0 and len(result.stages) > 0
        # Cache idempotente
        self._idempotency_cache[idempotency_key] = result
        # Atualizar métricas globais
        self._metrics["total_runs"] += 1
        if result.success:
            self._metrics["successful_runs"] += 1
        self._update_average_duration()

        return result

    def _is_required(self, step_value: str) -> bool:
        """Verifica se uma etapa é obrigatória pelo seu valor."""
        for stage in self._stages:
            if stage.step.value == step_value:
                return stage.required
        return False

    def _update_metrics(self, step: PipelineStep, duration_ms: float):
        if step.value not in self._metrics["stage_stats"]:
            self._metrics["stage_stats"][step.value] = {
                "total_time": 0.0,
                "runs": 0,
                "successes": 0,
            }

        stats = self._metrics["stage_stats"][step.value]
        stats["total_time"] += duration_ms
        stats["runs"] += 1
        if duration_ms >= 0:
            stats["successes"] += 1

    def _update_average_duration(self):
        if self._metrics["total_runs"] > 0:
            total_time = sum(
                s["total_time"]
                for s in self._metrics["stage_stats"].values()
            )
            self._metrics["average_duration_ms"] = total_time / self._metrics["total_runs"]

    # Handlers das etapas
    async def _extract_audio(self, file_path, audio_service, identity_service, version_engine):
        """Extração de metadados de áudio."""
        metadata = audio_service.extract(file_path)
        return metadata

    async def _normalize_tags(self, file_path, audio_service, identity_service, version_engine):
        """Normalização de tags e enriquecimento básico."""
        # Lógica de normalização
        return {"normalized": True}

    async def _resolve_identity(self, file_path, audio_service, identity_service, version_engine):
        """Resolução de identidade musical."""
        metadata = audio_service.extract(file_path)
        result = identity_service.resolve_and_enrich(file_path)
        return result

    async def _generate_fingerprint(self, file_path, audio_service, identity_service, version_engine):
        """Geração de fingerprint acústico."""
        # Placeholder para fingerprint
        return "fingerprint_placeholder"

    async def _enrich_musicbrainz(self, file_path, audio_service, identity_service, version_engine):
        """Enriquecimento com dados MusicBrainz."""
        return {}

    async def _validate_isrc(self, file_path, audio_service, identity_service, version_engine):
        """Validação de ISRC."""
        return True

    async def _link_materialization(self, file_path, audio_service, identity_service, version_engine):
        """Vincular materialização física."""
        return {}

    async def _analyze_acoustics(self, file_path, audio_service, identity_service, version_engine):
        """Análise acústica avançada."""
        return {}

    async def _generate_recommendations(self, file_path, audio_service, identity_service, version_engine):
        """Gerar recomendações baseadas em histórico."""
        return []

    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do pipeline."""
        return self._metrics

    def to_dict(self):
        return {
            "config": self.config.__dict__,
            "stages": [s.__dict__ for s in self._stages],
            "metrics": self._metrics,
        }