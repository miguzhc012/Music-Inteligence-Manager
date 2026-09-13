from dataclasses import dataclass
from typing import Optional, List
from uuid import uuid4

from mim.mcm.domain.recommendation import (
    Recommendation, RecommendationType, SimilarityAlgorithm,
    UserTasteProfile, AudioFeature
)
from mim.mcm.domain.ports import (
    RecommendationRepository, UserTasteProfileRepository,
    AudioFeatureRepository, HistoryRepository
)
from mim.mcm.domain.history import HistoryEvent, HistoryEventType


@dataclass
class RecommendationService:
    """Serviço de recomendação de músicas."""
    
    recommendation_repo: RecommendationRepository
    user_taste_repo: UserTasteProfileRepository
    audio_feature_repo: AudioFeatureRepository
    history_repo: HistoryRepository
    
    def get_recommendations(self, version_id: str, limit: int = 10) -> List[Recommendation]:
        """Obtém recomendações para uma versão."""
        # Tenta recomendações baseadas em similaridade acústica
        recommendations = self._recommend_by_audio_similarity(version_id, limit)
        
        # Se poucas, tenta baseada em histórico
        if len(recommendations) < limit:
            history_recs = self._recommend_by_history(version_id, limit - len(recommendations))
            recommendations.extend(history_recs)
        
        return recommendations[:limit]
    
    def get_recommendations_for_user(self, user_id: str, limit: int = 20) -> List[Recommendation]:
        """Obtém recomendações personalizadas para um usuário."""
        profile = self.user_taste_repo.get(user_id)
        if not profile:
            return []
        
        recommendations = []
        
        # Recomendações baseadas no gosto do usuário
        for artist in profile.favorite_artists[:3]:
            # TODO: Buscar artistas similares
            pass
        
        # Recomendações baseadas em histórico recente
        recent_events = self.history_repo.get_recent(limit=50)
        for event in recent_events:
            if event.event_type == HistoryEventType.PLAY and event.version_id:
                recs = self.get_recommendations(event.version_id, limit=5)
                recommendations.extend(recs)
        
        # Remove duplicatas e retorna
        seen = set()
        unique = []
        for rec in recommendations:
            if rec.target_version_id and rec.target_version_id not in seen:
                seen.add(rec.target_version_id)
                unique.append(rec)
        
        return unique[:limit]
    
    def _recommend_by_audio_similarity(self, version_id: str, limit: int) -> List[Recommendation]:
        """Recomendações baseadas em similaridade acústica."""
        feature = self.audio_feature_repo.get(version_id)
        if not feature:
            return []
        
        similar = self.audio_feature_repo.find_similar(feature, limit)
        recommendations = []
        
        for sim_feature in similar:
            rec = Recommendation(
                source_version_id=version_id,
                target_version_id=sim_feature.version_id,
                type=RecommendationType.SIMILAR_TRACKS,
                algorithm=SimilarityAlgorithm.COSINE_AUDIO,
                similarity_score=0.85,
                confidence=0.7,
            )
            recommendations.append(rec)
            self.recommendation_repo.add(rec)
        
        return recommendations
    
    def _recommend_by_history(self, version_id: str, limit: int) -> List[Recommendation]:
        """Recomendações baseadas no histórico do usuário."""
        # TODO: Implementar collaborative filtering
        return []
    
    def update_user_taste(self, user_id: str, played_version_id: str) -> None:
        """Atualiza o perfil de gosto do usuário baseado em uma reprodução."""
        profile = self.user_taste_repo.get(user_id)
        
        if profile is None:
            profile = UserTasteProfile(
                user_id=user_id,
                favorite_artists=[],
                favorite_genres=[],
                listening_count=0,
                total_ms_listened=0,
                skip_rate=0.0,
                repeat_rate=0.0,
            )
        
        # Atualiza contadores
        profile = UserTasteProfile(
            user_id=user_id,
            favorite_artists=profile.favorite_artists,
            favorite_genres=profile.favorite_genres,
            listening_count=profile.listening_count + 1,
            total_ms_listened=profile.total_ms_listened + 180000,  # ~3 min
            skip_rate=profile.skip_rate,
            repeat_rate=profile.repeat_rate,
        )
        
        self.user_taste_repo.update(profile)


class UserTasteService:
    """Serviço para gerenciar perfis de gosto do usuário."""
    
    def __init__(self, taste_repo: UserTasteProfileRepository):
        self.taste_repo = taste_repo
    
    def get_profile(self, user_id: str) -> Optional[UserTasteProfile]:
        """Obtém perfil de gosto de um usuário."""
        return self.taste_repo.get(user_id)
    
    def create_profile(self, user_id: str) -> UserTasteProfile:
        """Cria um novo perfil de gosto."""
        profile = UserTasteProfile(
            user_id=user_id,
            favorite_artists=[],
            favorite_genres=[],
            listening_count=0,
            total_ms_listened=0,
            skip_rate=0.0,
            repeat_rate=0.0,
        )
        self.taste_repo.add(profile)
        return profile
    
    def add_favorite_artist(self, user_id: str, artist: str) -> None:
        """Adiciona artista aos favoritos."""
        profile = self.taste_repo.get(user_id)
        if profile:
            if artist not in profile.favorite_artists:
                profile = UserTasteProfile(
                    user_id=user_id,
                    favorite_artists=profile.favorite_artists + [artist],
                    favorite_genres=profile.favorite_genres,
                    listening_count=profile.listening_count,
                    total_ms_listened=profile.total_ms_listened,
                    skip_rate=profile.skip_rate,
                    repeat_rate=profile.repeat_rate,
                )
                self.taste_repo.update(profile)