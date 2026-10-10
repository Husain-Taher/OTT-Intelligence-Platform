from typing import List, Tuple, Dict, Set
from app.models.schemas import CanonicalContent, UserTasteVector, RecommendationIntent, RecommendationItem
from app.intelligence.taste_engine import TasteEngine

class MultiStageRanker:
    @staticmethod
    def rank_and_diversify(
        candidates: List[Tuple[CanonicalContent, Dict[str, float]]],
        taste: UserTasteVector,
        intent: RecommendationIntent,
        top_n: int = 10,
        exclude_content_ids: Set[str] = set()
    ) -> List[Tuple[CanonicalContent, float, int, Dict[str, float], List[str], List[str], str]]:
        """
        Ranks candidates by combining personal match, intent alignment,
        quality signals, and novelty while enforcing strict mood gates and diversity.
        Returns: (content, final_score, personal_match_pct, breakdown, reasons, differences, contrast_note)
        """
        scored_items = []

        for item, gen_scores in candidates:
            if item.content_id in exclude_content_ids:
                continue

            prof = item.profile
            genres_lower = [g.lower() for g in item.genres]

            # 1. Base Personal Match from Taste Vector
            match_pct, breakdown, reasons, differences = TasteEngine.calculate_personal_match(taste, item)
            s_taste = match_pct / 100.0

            # 2. Strict Intent & Mood Scoring
            s_intent = 0.5
            mood_multiplier = 1.0

            if intent.mood:
                m = intent.mood.lower()
                if m in ["comforting", "wholesome", "light"]:
                    is_comforting = (
                        (prof and (prof.emotions.get("COMFORT", 0) > 0.4 or prof.emotions.get("JOY", 0) > 0.4)) or
                        any(g in genres_lower for g in ["comedy", "family", "animation"])
                    )
                    is_harsh = any(g in genres_lower for g in ["horror", "crime", "thriller"]) and not any(g in genres_lower for g in ["comedy", "family"])
                    if is_comforting:
                        s_intent = 0.95
                        mood_multiplier = 1.3
                    elif is_harsh:
                        s_intent = 0.05
                        mood_multiplier = 0.1

                elif m in ["exciting", "adrenaline", "action"]:
                    is_exciting = any(g in genres_lower for g in ["action", "adventure"]) or (prof and prof.emotions.get("TENSION", 0) > 0.6)
                    if is_exciting:
                        s_intent = 0.95
                        mood_multiplier = 1.3
                    else:
                        s_intent = 0.3
                        mood_multiplier = 0.7

                elif m in ["emotional", "poignant", "feel something"]:
                    is_emotional = (
                        (prof and (prof.emotions.get("REFLECTION", 0) > 0.55 or prof.emotions.get("SADNESS", 0) > 0.5 or prof.emotions.get("ROMANCE", 0) > 0.5)) or
                        "drama" in genres_lower or "romance" in genres_lower
                    )
                    if is_emotional:
                        s_intent = 0.92
                        mood_multiplier = 1.25
                    else:
                        s_intent = 0.35

                elif m in ["reflective", "intellectual", "philosophical"]:
                    is_reflective = (prof and prof.philosophical_depth > 0.6) or "science fiction" in genres_lower or "mystery" in genres_lower
                    if is_reflective:
                        s_intent = 0.95
                        mood_multiplier = 1.25
                    else:
                        s_intent = 0.35

                elif m in ["romance", "romantic", "love"]:
                    is_romance = (
                        (prof and prof.emotions.get("ROMANCE", 0) > 0.45) or
                        "romance" in genres_lower
                    )
                    if is_romance:
                        s_intent = 0.98
                        mood_multiplier = 1.35
                    else:
                        s_intent = 0.15
                        mood_multiplier = 0.4

                elif m in ["mystery", "whodunit", "puzzle"]:
                    is_mystery = (prof and prof.mystery > 0.6) or "mystery" in genres_lower
                    if is_mystery:
                        s_intent = 0.95
                        mood_multiplier = 1.3
                    else:
                        s_intent = 0.3

                elif m in ["strange", "weird", "surprise"]:
                    # Off the beaten path: non-US origin, or dense/uncanny storytelling
                    is_strange = (
                        any(c not in ("US", "GB") for c in item.origin_countries) or
                        (prof and (prof.narrative_complexity > 0.7 or prof.mystery > 0.7)) or
                        any(g in genres_lower for g in ["fantasy", "horror", "science fiction"])
                    )
                    if is_strange:
                        s_intent = 0.9
                        mood_multiplier = 1.25
                    else:
                        s_intent = 0.35

            # Target genres alignment boost or penalty
            if intent.target_genres:
                target_lower = [tg.lower() for tg in intent.target_genres]
                if any(g in target_lower for g in genres_lower):
                    s_intent = max(s_intent, 0.9)
                    mood_multiplier *= 1.2
                else:
                    mood_multiplier *= 0.6

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

            # Synthesize Final Score
            # If query_text is given, prioritize semantic match and intent over default taste profile
            if intent.query_text:
                w_taste = 0.10
                w_intent = 0.40
                w_semantic = 0.35
                w_quality = 0.10
                w_novelty = 0.05
            else:
                w_taste = 0.25
                w_intent = 0.35
                w_semantic = 0.20
                w_quality = 0.10
                w_novelty = novelty_weight * 0.10

            raw_score = (
                (s_taste * w_taste) +
                (s_intent * w_intent) +
                (s_semantic * w_semantic) +
                (s_quality * w_quality) +
                (s_novelty * w_novelty)
            ) * mood_multiplier - runtime_penalty

            final_score = max(0.01, min(1.0, raw_score))

            # Calibrate personal match percentage based on mood alignment
            adjusted_match_pct = int(min(99, max(30, match_pct * mood_multiplier - (runtime_penalty * 20))))

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

        # 7. Diversity Penalty (Maximal Marginal Relevance)
        selected: List[Tuple[CanonicalContent, float, int, Dict[str, float], List[str], List[str], str]] = []
        seen_genres: Dict[str, int] = {}
        seen_countries: Dict[str, int] = {}

        for entry in scored_items:
            item = entry[0]
            score = entry[1]

            primary_genre = item.genres[0] if item.genres else "Unknown"
            primary_country = item.origin_countries[0] if item.origin_countries else "Unknown"

            genre_count = seen_genres.get(primary_genre, 0)
            country_count = seen_countries.get(primary_country, 0)

            # Heavy penalty if already multiple titles of exact same genre and country
            penalty = (genre_count * 0.09) + (country_count * 0.07)
            adjusted_score = score - penalty

            selected.append((entry[0], round(adjusted_score, 3), entry[2], entry[3], entry[4], entry[5], entry[6]))
            seen_genres[primary_genre] = genre_count + 1
            seen_countries[primary_country] = country_count + 1

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
