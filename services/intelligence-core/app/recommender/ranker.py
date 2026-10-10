from typing import List, Tuple, Dict, Set
from app.models.schemas import CanonicalContent, UserTasteVector, RecommendationIntent, RecommendationItem
from app.intelligence.taste_engine import TasteEngine

class MultiStageRanker:
    @staticmethod
    def compute_mood_score(item: CanonicalContent, mood: str) -> float:
        """
        Evaluates content alignment for a specific mood from 0.0 to 1.0 using emotions,
        keywords, overview semantics, continuous darkness/intensity, and narrative aspects.
        """
        from app.intelligence.tagger import ContentTagger
        tag_res = ContentTagger.tag_content(item)
        m = mood.lower()

        alias_map = {
            "wholesome": "comforting", "light": "comforting", "cozy": "comforting",
            "adrenaline": "exciting", "action": "exciting",
            "poignant": "emotional", "feel something": "emotional",
            "intellectual": "reflective", "philosophical": "reflective",
            "whodunit": "mystery", "puzzle": "mystery",
            "romantic": "romance", "love": "romance",
            "weird": "strange", "surprise": "strange"
        }
        canonical = alias_map.get(m, m)
        return tag_res.mood_scores.get(canonical, 0.5)


    @staticmethod
    def rank_and_diversify(
        candidates: List[Tuple[CanonicalContent, Dict[str, float]]],
        taste: UserTasteVector,
        intent: RecommendationIntent,
        top_n: int = 10,
        exclude_content_ids: Set[str] = set(),
        shown_counts: Dict[str, int] = {}
    ) -> List[Tuple[CanonicalContent, float, int, Dict[str, float], List[str], List[str], str]]:
        """
        Ranks candidates by combining personal match, intent alignment,
        quality signals, and novelty while enforcing strict mood gates and diversity.
        Returns: (content, final_score, personal_match_pct, breakdown, reasons, differences, contrast_note)
        """
        scored_items = []

        # If user explicitly requested target genres, check if at least top_n match
        target_lower = [tg.lower() for tg in intent.target_genres] if intent.target_genres else []
        genre_matches_available = sum(1 for it, _ in candidates if any(g.lower() in target_lower for g in it.genres))

        for item, gen_scores in candidates:
            if item.content_id in exclude_content_ids:
                continue

            prof = item.profile
            genres_lower = [g.lower() for g in item.genres]

            # Hard Genre Filter: If requested genres exist in sufficient quantity (>= top_n), hard filter!
            if target_lower and genre_matches_available >= top_n:
                if not any(g in target_lower for g in genres_lower):
                    continue

            # Hard Mood Gate: drops candidates whose mood score is below 0.5
            s_mood = 0.5
            if intent.mood:
                s_mood = MultiStageRanker.compute_mood_score(item, intent.mood)
                if s_mood < 0.5:
                    continue

            # 1. Base Personal Match from Taste Vector
            match_pct, breakdown, reasons, differences = TasteEngine.calculate_personal_match(taste, item)
            s_taste = match_pct / 100.0

            # 2. Strict Intent & Mood Scoring
            s_intent = s_mood

            # Target genres alignment boost
            if target_lower:
                if any(g in target_lower for g in genres_lower):
                    s_intent = max(s_intent, 0.95)

            # Regional preference boost
            if intent.preferred_regions:
                if any(c in intent.preferred_regions for c in item.origin_countries):
                    s_intent += 0.25

            # 3. Semantic Score from NLP
            s_semantic = gen_scores.get("semantic_score", 0.5)

            # 4. Quality Signal (Normalized vote average & count)
            s_quality = min(1.0, max(0.0, (item.vote_average - 6.0) / 4.0)) if item.vote_average else 0.75

            # 5. Novelty / Exploration
            is_foreign = any(c not in ["US", "GB"] for c in item.origin_countries)
            novelty_weight = intent.novelty if intent.novelty is not None else 0.5
            s_novelty = 0.85 if (is_foreign and novelty_weight > 0.5) else 0.4

            # 6. Runtime Penalty
            runtime_penalty = 0.0
            if intent.max_runtime and item.runtime:
                if item.runtime > intent.max_runtime:
                    over = item.runtime - intent.max_runtime
                    runtime_penalty = min(0.6, (over / 25.0) * 0.25)

            # 7. Recent Session Shown Penalty (Phase 0 requirement 2)
            times_shown = shown_counts.get(item.content_id, 0)
            shown_penalty = times_shown * 0.16

            # Synthesize Final Score
            if intent.query_text:
                w_mood = 0.20
                w_taste = 0.10
                w_intent = 0.25
                w_semantic = 0.30
                w_quality = 0.10
                w_novelty = 0.05
            else:
                w_mood = 0.35
                w_taste = 0.20
                w_intent = 0.15
                w_semantic = 0.15
                w_quality = 0.10
                w_novelty = novelty_weight * 0.05

            raw_score = (
                (s_mood * w_mood) +
                (s_taste * w_taste) +
                (s_intent * w_intent) +
                (s_semantic * w_semantic) +
                (s_quality * w_quality) +
                (s_novelty * w_novelty)
            ) - runtime_penalty - shown_penalty

            final_score = max(0.01, min(1.0, raw_score))

            # Calibrate personal match percentage based on mood alignment
            adjusted_match_pct = int(min(99, max(30, (match_pct * 0.4 + s_mood * 60) - (runtime_penalty * 20))))

            # Formulate query-aware reasons if semantic or genre match
            adjusted_reasons = list(reasons)
            if intent.target_genres and any(g.lower() in [x.lower() for x in intent.target_genres] for g in item.genres):
                matched_g = [g for g in item.genres if g.lower() in [x.lower() for x in intent.target_genres]][0]
                adjusted_reasons.insert(0, f"Directly matches your search for {matched_g}")
            elif gen_scores.get("semantic_score", 0) > 0.15 and intent.query_text:
                adjusted_reasons.insert(0, f"Strong thematic alignment with '{intent.query_text}'")

            contrast_note = MultiStageRanker._generate_contrastive_note(item, taste, intent, adjusted_match_pct)

            scored_items.append((item, final_score, adjusted_match_pct, breakdown, adjusted_reasons, differences, contrast_note))

        # Sort by final score descending
        scored_items.sort(key=lambda x: x[1], reverse=True)

        # 8. Diversity Penalty (Maximal Marginal Relevance & Director/Franchise Cap)
        selected: List[Tuple[CanonicalContent, float, int, Dict[str, float], List[str], List[str], str]] = []
        seen_genres: Dict[str, int] = {}
        seen_countries: Dict[str, int] = {}
        seen_directors: Dict[str, int] = {}

        for entry in scored_items:
            item = entry[0]
            score = entry[1]

            primary_genre = item.genres[0] if item.genres else "Unknown"
            primary_country = item.origin_countries[0] if item.origin_countries else "Unknown"

            genre_count = seen_genres.get(primary_genre, 0)
            country_count = seen_countries.get(primary_country, 0)
            director_count = sum(seen_directors.get(d, 0) for d in item.directors)

            # Heavy penalty if already multiple titles of exact same genre, country or director
            penalty = (genre_count * 0.08) + (country_count * 0.06) + (director_count * 0.14)
            adjusted_score = score - penalty

            selected.append((entry[0], round(adjusted_score, 3), entry[2], entry[3], entry[4], entry[5], entry[6]))
            seen_genres[primary_genre] = genre_count + 1
            seen_countries[primary_country] = country_count + 1
            for d in item.directors:
                seen_directors[d] = seen_directors.get(d, 0) + 1

            if len(selected) >= top_n:
                break

        selected.sort(key=lambda x: x[1], reverse=True)
        return selected

    @staticmethod
    def _generate_contrastive_note(
        item: CanonicalContent,
        taste: UserTasteVector,
        intent: RecommendationIntent,
        match_pct: int
    ) -> str:
        prof = item.profile
        country_name = {"KR": "South Korea", "JP": "Japan", "FR": "France", "DE": "Germany", "IN": "India"}.get(
            item.origin_countries[0] if item.origin_countries else "US", "international cinema"
        )
        
        if intent.mood and intent.mood.lower() in ["comforting", "wholesome"]:
            return (
                f"Curated for tonight's comforting mood: {item.title} offers heartwarming character "
                f"warmth and high visual charm without anxiety or harsh narrative friction."
            )
        elif intent.mood and intent.mood.lower() in ["exciting", "adrenaline"]:
            return (
                f"Delivers an immediate kinetic surge with intense momentum and razor-sharp pacing, "
                f"calibrated for high-energy viewing tonight."
            )
        elif prof and prof.pacing.get("slow_build", 0) > 0.5:
            return (
                f"You respond strongly to slow-burn construction with morally layered characters. "
                f"{item.title} preserves this deliberate narrative build with a {match_pct}% taste fit."
            )
        elif prof and prof.philosophical_depth > 0.65:
            return (
                f"Matches your high appetite for thought-provoking world-building and existential mystery, "
                f"delivering an emotionally meaningful conclusion."
            )
        elif any(c in ["KR", "JP", "FR", "DE", "IN"] for c in item.origin_countries):
            return (
                f"Expands beyond domestic cinema into {country_name}, delivering distinct "
                f"cultural nuance and high narrative craft."
            )
        else:
            return f"Selected for tonight based on strong narrative alignment and verified audience consensus."
