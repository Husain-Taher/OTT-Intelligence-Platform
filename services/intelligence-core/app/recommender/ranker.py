from typing import List, Tuple, Dict, Set, Optional
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

            # Hard Genre Filter: If requested genres are specified, only allow matching items
            if target_lower:
                if not any(g in target_lower for g in genres_lower):
                    continue

            # Hard Mood Gate: strictly drops candidates whose mood score is below 0.6 (Phase 4 requirement)
            s_mood = 0.5
            if intent.mood:
                s_mood = MultiStageRanker.compute_mood_score(item, intent.mood)
                if s_mood < 0.6:
                    continue
                # If comforting, strictly exclude dark/violent/high-intensity titles
                if intent.mood.lower() == "comforting":
                    from app.intelligence.tagger import ContentTagger
                    dims = ContentTagger.compute_dimensions(item)
                    if dims["darkness"] > 0.35 or dims["intensity"] > 0.50:
                        continue

            # Hard Runtime Gate
            if intent.max_runtime and item.runtime and item.runtime > intent.max_runtime:
                continue

            # Hard Year Gate
            if intent.year_min and item.release_year and item.release_year < intent.year_min:
                continue
            if intent.year_max and item.release_year and item.release_year > intent.year_max:
                continue

            # Hard Rating Gate
            if intent.min_rating and item.vote_average and item.vote_average < intent.min_rating:
                continue

            # Hard Language Gate
            if intent.language and item.original_language and item.original_language.lower() != intent.language.lower():
                continue

            # Hard Masterpiece Gate
            if intent.masterpiece_only and not (item.vote_average and item.vote_average >= 8.0 and item.vote_count and item.vote_count >= 1000):
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

            # 4. Quality Signal (Normalized IMDb / TMDB vote average & vote volume)
            s_quality = min(1.0, max(0.0, (item.vote_average - 5.5) / 4.5)) if item.vote_average else 0.70

            # 5. Collaborative / Social Signal ("People like you liked this")
            from app.db.database import get_item_collaborative_affinity
            s_collab = get_item_collaborative_affinity(item.content_id)

            # 6. Novelty / Exploration
            is_foreign = any(c not in ["US", "GB"] for c in item.origin_countries)
            novelty_param = intent.novelty if intent.novelty is not None else 0.5
            s_novelty = (0.85 if is_foreign else 0.40) * (0.6 + 0.8 * novelty_param)
            s_novelty = min(1.0, max(0.1, s_novelty))

            # 7. Runtime Penalty
            runtime_penalty = 0.0
            if intent.max_runtime and item.runtime:
                if item.runtime > intent.max_runtime:
                    over = item.runtime - intent.max_runtime
                    runtime_penalty = min(0.6, (over / 25.0) * 0.25)

            # 8. Recent Session Shown Penalty (Phase 0 requirement 2)
            times_shown = shown_counts.get(item.content_id, 0)
            shown_penalty = times_shown * 0.16

            # Synthesize Final Score per Phase 5 Specification:
            # Baseline targets: Mood (0.35), Taste (0.25), Quality (0.15), Collaborative (0.15), Novelty (0.10)
            if intent.query_text:
                # Query-driven discovery: users expect direct relevance to what they typed!
                # If the item directly matched the search query (high semantic/keyword score), prioritize it over ambient mood
                w_semantic = 0.55
                w_quality = 0.20
                w_taste = 0.10
                w_collab = 0.05
                w_novelty = 0.05
                w_mood = 0.05

                raw_score = (
                    (s_semantic * w_semantic) +
                    (s_quality * w_quality) +
                    (s_taste * w_taste) +
                    (s_collab * w_collab) +
                    (s_novelty * w_novelty) +
                    (s_mood * w_mood)
                ) - runtime_penalty - shown_penalty
            else:
                w_mood = 0.35
                w_taste = 0.25
                w_quality = 0.15
                w_collab = 0.15
                w_novelty = 0.10

                raw_score = (
                    (s_mood * w_mood) +
                    (s_taste * w_taste) +
                    (s_quality * w_quality) +
                    (s_collab * w_collab) +
                    (s_novelty * w_novelty)
                ) - runtime_penalty - shown_penalty

            final_score = max(0.01, min(1.0, raw_score))

            # Calibrate personal match percentage based on mood alignment and taste
            adjusted_match_pct = int(min(99, max(30, (match_pct * 0.4 + s_mood * 60) - (runtime_penalty * 20))))

            # -----------------------------------------------------------------
            # Phase 7: Fact-Grounded Explanation Builder
            # Never hallucinate: build reasons strictly from verified database facts
            # (tagline, matching keywords, viewer review quotes, shared director/cast, primary cues)
            # -----------------------------------------------------------------
            fact_reasons = []

            # 1. Matching genres / query
            if intent.target_genres:
                matched_genres = [g for g in item.genres if any(tg.lower() == g.lower() for tg in intent.target_genres)]
                if matched_genres:
                    fact_reasons.append(f"Direct genre match: {', '.join(matched_genres)}")

            # 2. Tagline (Real TMDB fact)
            if item.tagline and len(item.tagline.strip()) > 5:
                clean_tagline = item.tagline.strip(' ".')
                fact_reasons.append(f'"{clean_tagline}"')

            # 3. Director / Auteur verification
            if item.directors:
                fact_reasons.append(f"Directed by {', '.join(item.directors[:2])}")

            # 4. Content cues and mood grounding
            from app.intelligence.tagger import ContentTagger
            tag_res = ContentTagger.tag_content(item)
            cues_for_mood = tag_res.primary_cues.get(intent.mood.lower(), []) if intent.mood else []
            if cues_for_mood:
                fact_reasons.append(f"Feeling: {cues_for_mood[0]}")

            # 5. Review quote excerpt (Real TMDB/audience quote)
            if prof and prof.highlighted_quotes:
                top_q = prof.highlighted_quotes[0]
                if top_q.text:
                    truncated_text = top_q.text if len(top_q.text) <= 90 else f"{top_q.text[:87]}..."
                    fact_reasons.append(f'Audience note: "{truncated_text}"')

            # 6. Thematic keywords
            if item.keywords and len(item.keywords) >= 2:
                fact_reasons.append(f"Themes: {', '.join(item.keywords[:3])}")

            # Fall back to taste engine reasons if list is short
            for r in reasons:
                if len(fact_reasons) >= 4:
                    break
                if r not in fact_reasons:
                    fact_reasons.append(r)

            contrast_note = MultiStageRanker._generate_contrastive_note(item, taste, intent, adjusted_match_pct)

            scored_items.append((item, final_score, adjusted_match_pct, breakdown, fact_reasons[:4], differences, contrast_note))

        # Sort candidate pool by final relevance score descending
        scored_items.sort(key=lambda x: x[1], reverse=True)

        # ---------------------------------------------------------------------
        # 8. Maximal Marginal Relevance (MMR) & Strict Director/Franchise Cap
        # MRR Formula: argmax_d [ lambda * Relevance(d) - (1 - lambda) * max_{s in S} Sim(d, s) ]
        # ---------------------------------------------------------------------
        from app.db.database import get_all_embeddings
        import numpy as np
        emb_map = get_all_embeddings()

        def extract_franchise(title: str) -> str:
            lower = title.strip().lower()
            for kw in [
                "harry potter", "lord of the rings", "godfather", "spider-man",
                "batman", "avatar", "dune", "knives out", "toy story", "avengers",
                "mission: impossible", "star wars", "jurassic", "fast & furious",
                "john wick", "matrix", "hunger games", "shrek"
            ]:
                if kw in lower:
                    return kw
            if ":" in title:
                return title.split(":")[0].strip().lower()
            return ""

        def get_item_vec(content_id: str) -> Optional[np.ndarray]:
            if content_id in emb_map and len(emb_map[content_id]) > 0:
                v = np.array(emb_map[content_id], dtype=np.float32)
                norm = np.linalg.norm(v)
                return (v / norm) if norm > 0 else v
            return None

        selected: List[Tuple[CanonicalContent, float, int, Dict[str, float], List[str], List[str], str]] = []
        selected_vectors: List[np.ndarray] = []
        selected_directors: Set[str] = set()
        selected_franchises: Set[str] = set()
        remaining = list(scored_items)

        # MMR balance parameter (lambda = 0.65 balances mood/quality relevance with distinctness)
        mmr_lambda = 0.65

        # If user explicitly searched for a specific franchise (e.g. "harry potter", "batman"), allow franchise sequels!
        queried_franchise = extract_franchise(intent.query_text) if intent.query_text else ""

        while remaining and len(selected) < top_n:
            best_idx = -1
            best_mmr_score = -999.0

            for idx, entry in enumerate(remaining):
                cand_item = entry[0]
                cand_rel = entry[1]

                # Hard Cap 1: Max 1 film per director per recommended set (unless explicit query)
                if not intent.query_text and any(d in selected_directors for d in cand_item.directors):
                    continue

                # Hard Cap 2: Max 1 film per franchise / universe per recommended set (unless querying that franchise)
                f_name = extract_franchise(cand_item.title)
                if f_name and f_name in selected_franchises and f_name != queried_franchise:
                    continue

                # Compute maximum similarity to any already selected item
                cand_vec = get_item_vec(cand_item.content_id)
                if selected_vectors and cand_vec is not None:
                    max_sim = max(float(np.dot(cand_vec, s_vec)) for s_vec in selected_vectors)
                else:
                    max_sim = 0.0

                mmr_val = (mmr_lambda * cand_rel) - ((1.0 - mmr_lambda) * max_sim)

                if mmr_val > best_mmr_score:
                    best_mmr_score = mmr_val
                    best_idx = idx

            # If no remaining candidate passed the hard caps (e.g. director overlap), relax caps to fill slots
            if best_idx == -1:
                # Pick the highest relevance score from remaining without hard blocking
                for idx, entry in enumerate(remaining):
                    cand_item = entry[0]
                    cand_rel = entry[1]
                    cand_vec = get_item_vec(cand_item.content_id)
                    max_sim = max((float(np.dot(cand_vec, s_vec)) for s_vec in selected_vectors), default=0.0)
                    mmr_val = (mmr_lambda * cand_rel) - ((1.0 - mmr_lambda) * max_sim)
                    if mmr_val > best_mmr_score:
                        best_mmr_score = mmr_val
                        best_idx = idx

            chosen_entry = remaining.pop(best_idx)
            chosen_item = chosen_entry[0]
            chosen_rel = chosen_entry[1]
            chosen_vec = get_item_vec(chosen_item.content_id)

            selected.append((
                chosen_item,
                round(chosen_rel, 3),
                chosen_entry[2],
                chosen_entry[3],
                chosen_entry[4],
                chosen_entry[5],
                chosen_entry[6]
            ))

            if chosen_vec is not None:
                selected_vectors.append(chosen_vec)
            for d in chosen_item.directors:
                selected_directors.add(d)
            f_cand = extract_franchise(chosen_item.title)
            if f_cand:
                selected_franchises.add(f_cand)

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
