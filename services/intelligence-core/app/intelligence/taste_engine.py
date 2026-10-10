from typing import Dict, List, Tuple, Optional
from app.models.schemas import UserTasteVector, CanonicalContent, UserInteractionEvent, ContentProfile

SIGNAL_WEIGHTS = {
    "POSTER_IMPRESSION": 0.05,
    "TITLE_OPEN": 0.2,
    "TRAILER_START": 0.3,
    "TRAILER_COMPLETE": 0.6,
    "WATCH_50_PERCENT": 0.8,
    "WATCH_COMPLETE": 1.0,
    "REWATCH": 1.4,
    "LIKE": 0.9,
    "SAVE": 0.7,
    "SHARE": 0.8,
    "ABANDON": -0.7,
    "DISLIKE": -1.3
}

class TasteEngine:
    @staticmethod
    def get_default_taste(user_id: str = "default_user") -> UserTasteVector:
        """
        Default initial taste vector representing an adventurous viewer
        who appreciates atmosphere, slow-burn narratives, and international cinema.
        """
        return UserTasteVector(
            user_id=user_id,
            genres={"Science Fiction": 0.85, "Mystery": 0.88, "Drama": 0.75, "Thriller": 0.82, "Crime": 0.70},
            narrative={"mystery": 0.85, "complexity": 0.80, "philosophical": 0.75, "character_driven": 0.82},
            emotions={"WONDER": 0.88, "SUSPENSE": 0.85, "REFLECTION": 0.80, "TENSION": 0.75, "HOPE": 0.65},
            pacing={"slow_build": 0.75, "medium": 0.65, "fast": 0.30},
            international={"KR": 0.82, "JP": 0.78, "FR": 0.65, "DE": 0.70, "IN": 0.60, "US": 0.75},
            preferred_directors={"Christopher Nolan": 0.9, "Denis Villeneuve": 0.9, "Bong Joon-ho": 0.88},
            abandoned_patterns={"cheap_jump_scares": 0.9, "aimless_dialogue": 0.6},
            interaction_count=12
        )

    @staticmethod
    def get_blank_taste(user_id: str) -> UserTasteVector:
        """Cold start for a real account: no assumptions, the profile is built from the user's own signals."""
        return UserTasteVector(user_id=user_id, interaction_count=0)

    @staticmethod
    def update_taste_with_event(taste: UserTasteVector, content: CanonicalContent, event_type: str) -> UserTasteVector:
        weight = SIGNAL_WEIGHTS.get(event_type, 0.2)
        prof = content.profile

        # 1. Update Genres
        for g in content.genres:
            cur = taste.genres.get(g, 0.5)
            # Dampened incremental update
            taste.genres[g] = round(max(0.0, min(1.0, cur + (weight * 0.08))), 3)

        # 2. Update Narrative & Pacing if profile exists
        if prof:
            for attr in ["mystery", "complexity", "philosophical", "character_driven"]:
                val = getattr(prof, f"narrative_{attr}", getattr(prof, attr, 0.5))
                cur_n = taste.narrative.get(attr, 0.5)
                taste.narrative[attr] = round(max(0.0, min(1.0, cur_n + (weight * 0.05 * val))), 3)

            # Update Pacing
            for pace_type, p_score in prof.pacing.items():
                cur_p = taste.pacing.get(pace_type, 0.5)
                taste.pacing[pace_type] = round(max(0.0, min(1.0, cur_p + (weight * 0.05 * p_score))), 3)

            # Update Emotions
            for emo, emo_score in prof.emotions.items():
                if emo_score >= 0.4:
                    cur_e = taste.emotions.get(emo, 0.5)
                    taste.emotions[emo] = round(max(0.0, min(1.0, cur_e + (weight * 0.05 * emo_score))), 3)

        # 3. Update International origin
        for c in content.origin_countries:
            cur_c = taste.international.get(c, 0.5)
            taste.international[c] = round(max(0.0, min(1.0, cur_c + (weight * 0.06))), 3)

        # 4. Handle Abandonment specific signals
        if event_type == "ABANDON":
            if prof and prof.pacing.get("slow_build", 0) > 0.65:
                taste.abandoned_patterns["excessive_slow_opening"] = round(min(1.0, taste.abandoned_patterns.get("excessive_slow_opening", 0.3) + 0.2), 2)

        taste.interaction_count += 1
        return taste

    @staticmethod
    def calculate_personal_match(taste: UserTasteVector, content: CanonicalContent) -> Tuple[int, Dict[str, float], List[str], List[str]]:
        """
        Calculates personal match percentage (0-100%), breakdown,
        matched reasons, and differences from usual.
        """
        prof = content.profile

        # 1. Genre Score
        genre_scores = [taste.genres.get(g, 0.4) for g in content.genres]
        g_match = sum(genre_scores) / len(genre_scores) if genre_scores else 0.5

        # 2. Narrative & Emotion Score
        n_match = 0.5
        e_match = 0.5
        p_match = 0.5

        if prof:
            n_scores = [
                abs(1.0 - abs(taste.narrative.get("mystery", 0.5) - prof.mystery)),
                abs(1.0 - abs(taste.narrative.get("complexity", 0.5) - prof.narrative_complexity)),
                abs(1.0 - abs(taste.narrative.get("philosophical", 0.5) - prof.philosophical_depth)),
                abs(1.0 - abs(taste.narrative.get("character_driven", 0.5) - prof.character_driven))
            ]
            n_match = sum(n_scores) / len(n_scores)

            # Top emotions alignment
            top_content_emotions = [k for k, v in prof.emotions.items() if v >= 0.5]
            if top_content_emotions:
                e_scores = [taste.emotions.get(emo, 0.4) for emo in top_content_emotions]
                e_match = sum(e_scores) / len(e_scores)

            # Pacing alignment
            dominant_pace = max(prof.pacing.items(), key=lambda x: x[1])[0]
            p_match = taste.pacing.get(dominant_pace, 0.5)

        # 3. International resonance
        country_scores = [taste.international.get(c, 0.5) for c in content.origin_countries]
        i_match = sum(country_scores) / len(country_scores) if country_scores else 0.55

        # Weighted aggregate
        total_score = (
            (g_match * 0.25) +
            (n_match * 0.30) +
            (e_match * 0.20) +
            (p_match * 0.15) +
            (i_match * 0.10)
        )

        match_pct = int(min(98, max(45, total_score * 100)))

        breakdown = {
            "narrative_alignment": round(n_match, 2),
            "emotional_resonance": round(e_match, 2),
            "pacing_fit": round(p_match, 2),
            "genre_affinity": round(g_match, 2),
            "regional_affinity": round(i_match, 2)
        }

        # Matched reasons (Evidence)
        reasons = []
        if prof and prof.pacing.get("slow_build", 0) > 0.5 and taste.pacing.get("slow_build", 0) > 0.6:
            reasons.append("Matches your slow-burn preference")
        elif prof and prof.pacing.get("fast", 0) > 0.4 and taste.pacing.get("fast", 0) > 0.5:
            reasons.append("Matches your fast-paced kinetic preference")

        if prof and prof.mystery > 0.7 and taste.narrative.get("mystery", 0) > 0.7:
            reasons.append("Strong narrative mystery & investigative payoff")

        if prof and prof.character_driven > 0.7:
            reasons.append("Deep, character-driven moral construction")

        if any(c in ["KR", "JP", "FR", "DE", "IN"] for c in content.origin_countries):
            country_name = {"KR": "Korean", "JP": "Japanese", "FR": "French", "DE": "German", "IN": "Indian"}.get(content.origin_countries[0], "International")
            reasons.append(f"Aligns with your interest in {country_name} storytelling")

        if not reasons:
            reasons.append(f"Strong overlap with your favorite {content.genres[0] if content.genres else 'cinematic'} themes")

        # Differences from usual (for transparent discovery)
        differences = []
        if content.runtime and content.runtime <= 100:
            differences.append("Shorter, more compact runtime than your usual 2h+ picks")
        if any(c not in ["US", "GB"] for c in content.origin_countries):
            c_name = {"KR": "South Korea", "JP": "Japan", "FR": "France", "DE": "Germany", "IN": "India"}.get(content.origin_countries[0], "Global")
            differences.append(f"Set in {c_name} instead of domestic releases")
        if prof and prof.aspect_breakdown.ending_satisfaction >= 85:
            differences.append("High ending satisfaction consensus")

        return match_pct, breakdown, reasons, differences
