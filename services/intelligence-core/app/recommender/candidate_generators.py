from typing import List, Dict, Set, Tuple
from app.models.schemas import CanonicalContent, UserTasteVector, RecommendationIntent, ContentType
from app.intelligence.taste_engine import TasteEngine
from app.intelligence.semantic_engine import SemanticEngine

class CandidateGenerator:
    def __init__(self, semantic_engine: SemanticEngine):
        self.semantic = semantic_engine

    def generate_candidates(
        self,
        all_items: List[CanonicalContent],
        taste: UserTasteVector,
        intent: RecommendationIntent,
        seen_content_ids: Set[str] = set()
    ) -> List[Tuple[CanonicalContent, Dict[str, float]]]:
        """
        Retrieves up to 50 candidates from diverse generators:
        1. Content-based Taste Matching
        2. Semantic Intent Matching
        3. Regional / Cross-Cultural Discovery
        4. Novelty & Exploration Generator
        """
        candidates_map: Dict[str, Tuple[CanonicalContent, Dict[str, float]]] = {}
        items_by_id = {item.content_id: item for item in all_items}

        # 1. Semantic & Intent Retrieval
        query = intent.query_text or ""
        search_terms = [query]
        if intent.mood:
            search_terms.append(f"{intent.mood} atmospheric")
        if intent.target_genres:
            search_terms.append(" ".join(intent.target_genres))
        if intent.preferred_regions:
            search_terms.append(" ".join(intent.preferred_regions))

        full_search_str = " ".join(search_terms).strip()
        semantic_hits = self.semantic.search_semantic(full_search_str, items_by_id, top_k=35) if full_search_str else []
        for item, sim_score in semantic_hits:
            if item.content_id in seen_content_ids:
                continue
            candidates_map[item.content_id] = (item, {"semantic_score": sim_score, "source": "semantic"})

        # Also retrieve directly if item matches target_genres or keyword
        if intent.target_genres:
            for item in all_items:
                if item.content_id in seen_content_ids or item.content_id in candidates_map:
                    continue
                if any(g in item.genres for g in intent.target_genres):
                    candidates_map[item.content_id] = (item, {"semantic_score": 0.35, "source": "genre_match"})

        # Retrieve candidates matching the requested mood
        if intent.mood:
            from app.recommender.ranker import MultiStageRanker
            for item in all_items:
                if item.content_id in seen_content_ids or item.content_id in candidates_map:
                    continue
                m_score = MultiStageRanker.compute_mood_score(item, intent.mood)
                if m_score >= 0.5:
                    candidates_map[item.content_id] = (item, {"semantic_score": m_score * 0.7, "source": "mood_match"})


        # 2. Taste-Based Retrieval (Only backfill if no explicit query text or as soft candidate addition)
        if not intent.query_text:
            for item in all_items:
                if item.content_id in seen_content_ids or item.content_id in candidates_map:
                    continue
                match_pct, _, _, _ = TasteEngine.calculate_personal_match(taste, item)
                taste_score = match_pct / 100.0
                if taste_score >= 0.65:
                    candidates_map[item.content_id] = (item, {"taste_score": taste_score, "source": "taste"})
        else:
            # If query_text is present, only add taste items if they have semantic or mood overlap
            for item in all_items:
                if item.content_id in seen_content_ids or item.content_id in candidates_map:
                    continue
                if intent.mood and item.profile and item.profile.emotions.get(intent.mood.upper(), 0) > 0.3:
                    candidates_map[item.content_id] = (item, {"taste_score": 0.5, "source": "mood_taste"})

        # 3. Novelty & Cross-Cultural Exploration Generator
        if not intent.query_text:
            for item in all_items:
                if item.content_id in seen_content_ids or item.content_id in candidates_map:
                    continue
                if item.vote_average >= 7.8 and any(c in ["KR", "JP", "FR", "DE", "IN"] for c in item.origin_countries):
                    candidates_map[item.content_id] = (item, {"exploration_score": 0.85, "source": "exploration"})

        # 4. Contextual Hard Constraints Filter (Runtime, Negative Tags)
        filtered_candidates = []
        for cid, (item, scores) in candidates_map.items():
            # Runtime constraint
            if intent.max_runtime and item.runtime:
                if item.runtime > (intent.max_runtime + 10):
                    continue

            # Avoid tags constraint
            prof = item.profile
            if prof and "high_complexity" in intent.avoid_tags and prof.narrative_complexity > 0.75:
                continue
            if prof and "depression" in intent.avoid_tags and prof.emotions.get("SADNESS", 0) > 0.65 and prof.emotions.get("HOPE", 0) < 0.4:
                continue

            filtered_candidates.append((item, scores))

        return filtered_candidates
