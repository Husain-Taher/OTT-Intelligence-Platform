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
        search_terms = []
        if query:
            search_terms.append(query)
        elif intent.mood:
            search_terms.append(f"{intent.mood} atmospheric")
        if intent.target_genres and not query:
            search_terms.append(" ".join(intent.target_genres))
        if intent.preferred_regions and not query:
            search_terms.append(" ".join(intent.preferred_regions))

        full_search_str = " ".join(search_terms).strip()
        semantic_hits = self.semantic.search_semantic(full_search_str, items_by_id, top_k=60) if full_search_str else []
        for item, sim_score in semantic_hits:
            if item.content_id in seen_content_ids:
                continue
            candidates_map[item.content_id] = (item, {"semantic_score": sim_score, "source": "semantic"})

        # Typo-tolerant keyword / title / person retrieval
        if query and hasattr(self.semantic, "search_keyword"):
            keyword_hits = self.semantic.search_keyword(query, top_k=15)
            for hit in keyword_hits:
                item = hit["content"]
                if item.content_id not in seen_content_ids and item.content_id not in candidates_map:
                    candidates_map[item.content_id] = (item, {"semantic_score": hit["score"], "source": hit["match_reason"]})


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
                    s_score = 0.2 if intent.query_text else (m_score * 0.7)
                    candidates_map[item.content_id] = (item, {"semantic_score": s_score, "source": "mood_match"})


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

        # 4. Contextual Hard Constraints & Retrieval Gating (Phase 4)
        from app.recommender.ranker import MultiStageRanker
        filtered_candidates = []

        # If user explicitly requested target genres
        target_genres_lower = [tg.lower() for tg in intent.target_genres] if intent.target_genres else []

        for cid, (item, scores) in candidates_map.items():
            # 1. Hard Mood Gating: mood score must be >= 0.6 (Phase 4 requirement)
            if intent.mood:
                m_score = MultiStageRanker.compute_mood_score(item, intent.mood)
                if m_score < 0.6:
                    continue
                # If comforting, strictly exclude dark/violent/high-intensity titles
                if intent.mood.lower() == "comforting":
                    from app.intelligence.tagger import ContentTagger
                    dims = ContentTagger.compute_dimensions(item)
                    if dims["darkness"] > 0.35 or dims["intensity"] > 0.50:
                        continue

            # 2. Hard Genre Filter: if target_genres is provided, item must contain at least one requested genre
            if target_genres_lower:
                item_genres_lower = [g.lower() for g in item.genres]
                if not any(tg in item_genres_lower for tg in target_genres_lower):
                    continue

            # 3. Hard Runtime Filter: runtime must not exceed max_runtime
            if intent.max_runtime and item.runtime:
                if item.runtime > intent.max_runtime:
                    continue

            # 4. Hard Year Range Gating
            if intent.year_min and item.release_year and item.release_year < intent.year_min:
                continue
            if intent.year_max and item.release_year and item.release_year > intent.year_max:
                continue

            # 5. Hard Rating Threshold
            if intent.min_rating and item.vote_average and item.vote_average < intent.min_rating:
                continue

            # 6. Hard Language Filter
            if intent.language and item.original_language:
                if item.original_language.lower() != intent.language.lower():
                    continue

            # 7. Hard Masterpiece Filter: rating >= 8.0 and substantial vote count
            if intent.masterpiece_only:
                if not (item.vote_average and item.vote_average >= 8.0 and item.vote_count and item.vote_count >= 1000):
                    continue

            # 8. Avoid tags constraint
            prof = item.profile
            if prof and "high_complexity" in intent.avoid_tags and prof.narrative_complexity > 0.75:
                continue
            if prof and "depression" in intent.avoid_tags and prof.emotions.get("SADNESS", 0) > 0.65 and prof.emotions.get("HOPE", 0) < 0.4:
                continue

            filtered_candidates.append((item, scores))

        return filtered_candidates
