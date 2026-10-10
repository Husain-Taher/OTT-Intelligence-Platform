"""
Content Tagging Engine for OTT Intelligence Platform.
Computes fine-grained scores (0.0 to 1.0) for:
- 7 Core Moods: comforting, emotional, reflective, mystery, exciting, romance, strange
- 3 Continuous Dimensions: pace, darkness, intensity

Derived systematically from plot overview, keywords, emotions, aspect ratings,
and review excerpts rather than coarse genre heuristics alone.
"""
import re
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from app.models.schemas import CanonicalContent, EmotionType

DARKNESS_KEYWORDS = [
    "murder", "death", "serial killer", "killer", "deadly", "torture", "dystopia", "dystopian",
    "suicide", "corruption", "grim", "cynical", "bleak", "nightmare", "apocalypse", "gore",
    "bloody", "terror", "paranoia", "revenge", "violence", "violent", "sinister", "evil",
    "depressing", "brutal", "gruesome", "macabre", "grief", "tragic", "darkness", "nihilism",
    "slaughter", "massacre", "demon", "demons", "zombie", "horror", "haunted", "devil",
    "psychopath", "dark comedy", "black comedy", "caste violence", "infiltration", "con artist",
    "disturbing", "frightening", "terrifying", "menace", "hostage", "assassin", "conspiracy"
]

BRIGHTNESS_KEYWORDS = [
    "wholesome", "heartwarming", "feel-good", "friendship", "family friendly", "uplifting",
    "cheerful", "joy", "joyful", "charming", "sweet", "gentle", "delightful", "funny",
    "hilarious", "comforting", "kindness", "healing", "cozy", "laugh", "hope", "optimistic",
    "innocence", "tender", "warmhearted", "whimsy", "playful"
]

INTENSITY_KEYWORDS = [
    "relentless", "adrenaline", "explosive", "panic", "life or death", "chase", "survival",
    "catastrophe", "heart-pounding", "frenetic", "non-stop", "kinetic", "stunt", "fury",
    "warfare", "bomb", "shootout", "combat", "cataclysmic", "unrelenting", "nerve-wracking",
    "overwhelming", "action-packed", "high octane", "chaotic", "furious", "battle", "fight",
    "clash", "showdown", "bloodshed", "martial arts", "desperate"
]

GENTLE_KEYWORDS = [
    "gentle", "soothing", "cozy", "calm", "peaceful", "slow burn", "relaxed", "unhurried",
    "quiet", "serene", "tranquil", "mild", "meditative", "low-key", "contemplative", "peaceable"
]

SURREAL_KEYWORDS = [
    "surreal", "bizarre", "weird", "mind-bending", "multiverse", "time travel", "dream",
    "hallucination", "supernatural", "unreal", "alien", "simulation", "dystopian", "paradox",
    "alternate reality", "uncanny", "psychedelic", "nightmarish", "absurd", "eccentric",
    "existential dread", "parallel universe", "cursed", "demon", "evil spirit", "other dimension",
    "possession", "mythology", "zombie", "infection", "biological weapon"
]


class ContentTagResult(BaseModel):
    mood_scores: Dict[str, float] = Field(default_factory=dict)
    pace: float = Field(0.5, ge=0.0, le=1.0)
    darkness: float = Field(0.5, ge=0.0, le=1.0)
    intensity: float = Field(0.5, ge=0.0, le=1.0)
    primary_cues: Dict[str, List[str]] = Field(default_factory=dict)


class ContentTagger:
    @staticmethod
    def _count_keyword_matches(text: str, keywords: List[str]) -> int:
        return sum(len(re.findall(r'\b' + re.escape(kw) + r'\b', text)) for kw in keywords)

    @classmethod
    def compute_dimensions(cls, item: CanonicalContent) -> Dict[str, float]:
        """
        Computes the three continuous dimensions:
        - darkness (0.0 to 1.0)
        - intensity (0.0 to 1.0)
        - pace (0.0 to 1.0)
        """
        genres_lower = [g.lower() for g in item.genres]
        keywords_lower = [k.lower() for k in (item.keywords or [])]
        overview_lower = (item.overview or "").lower()
        tagline_lower = (item.tagline or "").lower()
        full_text = f"{overview_lower} {tagline_lower} {' '.join(keywords_lower)}"

        prof = item.profile
        emotions = prof.emotions if prof else {}

        # 1. DARKNESS
        dark_matches = cls._count_keyword_matches(full_text, DARKNESS_KEYWORDS)
        bright_matches = cls._count_keyword_matches(full_text, BRIGHTNESS_KEYWORDS)

        fear_val = emotions.get("FEAR", 0.0)
        grief_val = emotions.get("GRIEF", 0.0)
        sad_val = emotions.get("SADNESS", 0.0)
        tension_val = emotions.get("TENSION", 0.0)
        suspense_val = emotions.get("SUSPENSE", 0.0)
        joy_val = emotions.get("JOY", 0.0)
        comfort_val = emotions.get("COMFORT", 0.0)

        base_darkness = 0.20

        # Genre baseline
        if "horror" in genres_lower:
            base_darkness += 0.55
        elif "crime" in genres_lower:
            base_darkness += 0.35
        elif "thriller" in genres_lower:
            base_darkness += 0.30
        elif "war" in genres_lower:
            base_darkness += 0.40

        is_dark_comedy = any(k in full_text for k in ["dark comedy", "black comedy", "satire"])
        has_thriller_or_crime = any(g in genres_lower for g in ["thriller", "crime", "horror", "mystery"])

        if ("family" in genres_lower or "animation" in genres_lower) and not has_thriller_or_crime and not any(k in full_text for k in ["demon", "violence", "horror"]):
            base_darkness -= 0.15

        if "comedy" in genres_lower and not is_dark_comedy and not has_thriller_or_crime:
            base_darkness -= 0.12

        # Keyword amplification
        base_darkness += min(0.45, dark_matches * 0.09)
        if not is_dark_comedy and not has_thriller_or_crime:
            base_darkness -= min(0.35, bright_matches * 0.09)

        # Emotional profile amplification
        emo_dark_pull = (fear_val * 0.40) + (grief_val * 0.25) + (sad_val * 0.20) + (tension_val * 0.25) + (suspense_val * 0.20)
        base_darkness += (emo_dark_pull * 0.35)

        # Only let joy/comfort reduce darkness if fear and tension are low
        if fear_val < 0.35 and tension_val < 0.45 and not has_thriller_or_crime:
            emo_bright_pull = (joy_val * 0.30) + (comfort_val * 0.35)
            base_darkness -= (emo_bright_pull * 0.25)

        darkness = max(0.02, min(0.98, round(base_darkness, 3)))

        # 2. INTENSITY
        intense_matches = cls._count_keyword_matches(full_text, INTENSITY_KEYWORDS)
        gentle_matches = cls._count_keyword_matches(full_text, GENTLE_KEYWORDS)

        base_intensity = 0.25
        if "action" in genres_lower:
            base_intensity += 0.40
        elif "adventure" in genres_lower:
            base_intensity += 0.25
        if "thriller" in genres_lower:
            base_intensity += 0.25
        if "horror" in genres_lower:
            base_intensity += 0.30

        if any(w in full_text for w in ["demon", "demons", "battle", "fight", "war", "survival"]):
            base_intensity += 0.20

        base_intensity += min(0.45, intense_matches * 0.09)
        base_intensity -= min(0.30, gentle_matches * 0.09)

        awe_val = emotions.get("AWE", 0.0)
        emo_intense_pull = (tension_val * 0.45) + (suspense_val * 0.35) + (fear_val * 0.25) + (awe_val * 0.15)
        base_intensity += (emo_intense_pull * 0.30)
        if gentle_matches > 0:
            base_intensity -= (comfort_val * 0.20)

        intensity = max(0.02, min(0.98, round(base_intensity, 3)))

        # 3. PACE (0.0 slow burn to 1.0 frenetic)
        if prof and prof.pacing:
            p_slow = prof.pacing.get("slow_build", 0.33)
            p_fast = prof.pacing.get("fast", 0.33)
            base_pace = 0.5 + ((p_fast - p_slow) * 0.5)
        else:
            base_pace = 0.5
            if "action" in genres_lower:
                base_pace += 0.25
            elif "drama" in genres_lower or "mystery" in genres_lower:
                base_pace -= 0.15

        if intense_matches > 1 or "action" in genres_lower:
            base_pace += 0.15
        if gentle_matches > 1:
            base_pace -= 0.15

        if item.runtime and item.runtime > 150:
            base_pace -= 0.08

        pace = max(0.05, min(0.95, round(base_pace, 3)))

        return {
            "darkness": darkness,
            "intensity": intensity,
            "pace": pace
        }

    @classmethod
    def tag_content(cls, item: CanonicalContent) -> ContentTagResult:
        """
        Produces full tagging profile including darkness, intensity, pace,
        and continuous 0.0 - 1.0 scores for each of the 7 core moods with explanatory cues.
        """
        dims = cls.compute_dimensions(item)
        darkness = dims["darkness"]
        intensity = dims["intensity"]
        pace = dims["pace"]

        genres_lower = [g.lower() for g in item.genres]
        keywords_lower = [k.lower() for k in (item.keywords or [])]
        overview_lower = (item.overview or "").lower()
        tagline_lower = (item.tagline or "").lower()
        full_text = f"{overview_lower} {tagline_lower} {' '.join(keywords_lower)}"

        prof = item.profile
        emotions = prof.emotions if prof else {}

        mood_scores: Dict[str, float] = {}
        primary_cues: Dict[str, List[str]] = {}

        # -------------------------------------------------------------------------
        # 1. COMFORTING (Warm, cozy, gentle, lighthearted, wholesome)
        # -------------------------------------------------------------------------
        c_cues = []
        c_score = 0.20
        joy_val = emotions.get("JOY", 0.0)
        comfort_val = emotions.get("COMFORT", 0.0)
        hope_val = emotions.get("HOPE", 0.0)
        fear_val = emotions.get("FEAR", 0.0)
        tension_val = emotions.get("TENSION", 0.0)
        suspense_val = emotions.get("SUSPENSE", 0.0)

        wonder_val = emotions.get("WONDER", 0.0)
        # Baseline positive signals
        if joy_val > 0.35:
            c_score += joy_val * 0.3
            c_cues.append(f"Uplifting Joy ({int(joy_val*100)}%)")
        if comfort_val > 0.35:
            c_score += comfort_val * 0.35
            c_cues.append(f"Heartwarming Comfort ({int(comfort_val*100)}%)")
        if hope_val > 0.4:
            c_score += 0.15
            c_cues.append("Optimistic Outlook")
        if wonder_val > 0.45 and darkness < 0.20:
            c_score += 0.18
            c_cues.append(f"Gentle Wonder ({int(wonder_val*100)}%)")

        bright_cnt = cls._count_keyword_matches(full_text, BRIGHTNESS_KEYWORDS)
        if bright_cnt > 0:
            c_score += min(0.30, bright_cnt * 0.10)
            c_cues.append("Wholesome Narrative")

        if any(g in genres_lower for g in ["animation", "family", "comedy"]):
            c_score += 0.20
        if any(g in genres_lower for g in ["family"]) and any(g in genres_lower for g in ["animation"]) and darkness < 0.15:
            c_score += 0.12

        # Hard exclusions & steep dampeners:
        # High darkness, high intensity, thriller/horror/war, violence, or high fear/tension
        # completely disqualify a title from Comforting!
        is_hard_excluded = False
        if any(g in genres_lower for g in ["horror", "war", "thriller"]):
            is_hard_excluded = True
            c_cues.append("Excluded: Genre has Thriller/Horror/War tension")

        if any(k in full_text for k in ["dark comedy", "caste violence", "demon", "serial killer", "torture", "murder", "bloody", "massacre"]):
            is_hard_excluded = True
            c_cues.append("Excluded: Dark/Violent Content Cues")

        if fear_val > 0.38 or tension_val > 0.50 or suspense_val > 0.65:
            is_hard_excluded = True
            c_cues.append("Excluded: High Fear/Tension/Suspense Profile")

        if is_hard_excluded:
            c_score = 0.0
        else:
            # Steep continuous penalties for darkness and intensity
            if darkness > 0.30:
                c_score -= (darkness - 0.30) * 2.5
            if intensity > 0.45:
                c_score -= (intensity - 0.45) * 2.5

        mood_scores["comforting"] = max(0.0, min(1.0, round(c_score, 3)))
        primary_cues["comforting"] = c_cues[:4]

        # -------------------------------------------------------------------------
        # 2. EXCITING (High adrenaline, kinetic, high action/suspense)
        # -------------------------------------------------------------------------
        e_cues = []
        e_score = (intensity * 0.50) + (pace * 0.35)
        e_cues.append(f"Kinetic Intensity ({int(intensity*100)}%)")
        e_cues.append(f"Fast-paced Rhythm ({int(pace*100)}%)")

        if any(g in genres_lower for g in ["action", "adventure"]):
            e_score += 0.20
            e_cues.append("Action Spectacle")
        if tension_val > 0.45 or suspense_val > 0.5:
            e_score += 0.15
            e_cues.append("High Stakes Tension")

        intense_cnt = cls._count_keyword_matches(full_text, INTENSITY_KEYWORDS)
        if intense_cnt > 0:
            e_score += min(0.25, intense_cnt * 0.07)

        mood_scores["exciting"] = max(0.0, min(1.0, round(e_score, 3)))
        primary_cues["exciting"] = e_cues[:4]

        # -------------------------------------------------------------------------
        # 3. EMOTIONAL (Poignant drama, heartbreak, catharsis, moving)
        # -------------------------------------------------------------------------
        em_cues = []
        em_score = 0.15
        sad_val = emotions.get("SADNESS", 0.0)
        grief_val = emotions.get("GRIEF", 0.0)
        refl_val = emotions.get("REFLECTION", 0.0)
        rom_val = emotions.get("ROMANCE", 0.0)

        if sad_val > 0.3:
            em_score += sad_val * 0.35
            em_cues.append(f"Deep Poignancy ({int(sad_val*100)}%)")
        if grief_val > 0.3:
            em_score += grief_val * 0.30
            em_cues.append(f"Emotional Catharsis ({int(grief_val*100)}%)")
        if refl_val > 0.4:
            em_score += refl_val * 0.20
        if rom_val > 0.4:
            em_score += rom_val * 0.15
            em_cues.append("Heartfelt Intimacy")

        if "drama" in genres_lower:
            em_score += 0.20
            em_cues.append("Character-driven Drama")
        if prof and prof.character_driven > 0.65:
            em_score += 0.15

        # Extreme kinetic intensity / action thriller dampener for pure emotional drama
        if intensity > 0.75:
            em_score -= (intensity - 0.75) * 1.2

        mood_scores["emotional"] = max(0.0, min(1.0, round(em_score, 3)))
        primary_cues["emotional"] = em_cues[:4]

        # -------------------------------------------------------------------------
        # 4. REFLECTIVE (Philosophical, existential, thought-provoking, deep)
        # -------------------------------------------------------------------------
        r_cues = []
        phil_depth = prof.philosophical_depth if prof else 0.4
        r_score = 0.05 + (phil_depth * 0.50)
        if phil_depth > 0.6:
            r_cues.append(f"Philosophical Depth ({int(phil_depth*100)}%)")

        if refl_val > 0.4:
            r_score += refl_val * 0.25
            r_cues.append("Thought-provoking Reflection")

        wonder_val = emotions.get("WONDER", 0.0)
        if wonder_val > 0.4:
            r_score += wonder_val * 0.15
            r_cues.append("Existential Wonder")

        if any(g in genres_lower for g in ["science fiction", "documentary"]):
            r_score += 0.15
        elif "drama" in genres_lower and phil_depth > 0.60:
            r_score += 0.10

        if pace < 0.45:
            r_score += 0.15
            r_cues.append("Deliberate Meditative Pace")

        # Romantic comedies / lighthearted romance are not primary philosophical reflections
        if "romance" in genres_lower and "comedy" in genres_lower and phil_depth < 0.70:
            r_score -= 0.35

        # Kinetic / explosive action penalty for Reflective
        if intensity > 0.70:
            r_score -= (intensity - 0.70) * 1.5

        mood_scores["reflective"] = max(0.0, min(1.0, round(r_score, 3)))
        primary_cues["reflective"] = r_cues[:4]

        # -------------------------------------------------------------------------
        # 5. MYSTERY (Puzzle, investigation, whodunit, secrets, twists)
        # -------------------------------------------------------------------------
        m_cues = []
        mystery_depth = prof.mystery if prof else (0.8 if "mystery" in genres_lower else 0.4)
        m_score = 0.15 + (mystery_depth * 0.45)
        if mystery_depth > 0.55:
            m_cues.append(f"Intriguing Mystery ({int(mystery_depth*100)}%)")

        curiosity_val = emotions.get("CURIOSITY", 0.0)
        if suspense_val > 0.35:
            m_score += suspense_val * 0.25
            m_cues.append("Gripping Suspense")
        if curiosity_val > 0.35:
            m_score += curiosity_val * 0.15

        if "mystery" in genres_lower:
            m_score += 0.25
            m_cues.append("Genre Investigation")
        elif any(g in genres_lower for g in ["crime", "thriller"]):
            m_score += 0.15

        if any(w in full_text for w in ["detective", "murder", "whodunit", "clues", "secret", "investigation"]):
            m_score += 0.15
            m_cues.append("Investigative Puzzles")

        mood_scores["mystery"] = max(0.0, min(1.0, round(m_score, 3)))
        primary_cues["mystery"] = m_cues[:4]

        # -------------------------------------------------------------------------
        # 6. ROMANCE (Love, chemistry, romantic passion, intimacy)
        # -------------------------------------------------------------------------
        ro_cues = []
        ro_score = 0.05
        if rom_val > 0.25:
            ro_score += rom_val * 0.55
            ro_cues.append(f"Romantic Passion ({int(rom_val*100)}%)")
        if "romance" in genres_lower:
            ro_score += 0.40
            ro_cues.append("Romantic Centerpiece")
        if any(w in full_text for w in ["love", "couple", "relationship", "marriage", "lover", "passion"]):
            ro_score += 0.20
            ro_cues.append("Intimate Relationship Focus")

        if darkness > 0.65 and rom_val < 0.4:
            ro_score -= 0.30

        mood_scores["romance"] = max(0.0, min(1.0, round(ro_score, 3)))
        primary_cues["romance"] = ro_cues[:4]

        # -------------------------------------------------------------------------
        # 7. STRANGE (Surreal, weird, bizarre, uncanny, mind-bending)
        # -------------------------------------------------------------------------
        s_cues = []
        s_score = 0.05
        complexity = prof.narrative_complexity if prof else 0.5
        if complexity > 0.65:
            s_score += (complexity - 0.4) * 0.45
            s_cues.append(f"Non-linear Complexity ({int(complexity*100)}%)")

        surreal_cnt = cls._count_keyword_matches(full_text, SURREAL_KEYWORDS)
        if surreal_cnt > 0:
            s_score += min(0.50, surreal_cnt * 0.16)
            s_cues.append("Bizarre / Surreal Themes")

        if any(g in genres_lower for g in ["fantasy", "horror", "science fiction"]):
            s_score += 0.15

        if darkness > 0.55 and complexity > 0.55:
            s_score += 0.15
            s_cues.append("Dark Uncanny Atmosphere")

        # Straightforward comedy without surreal keywords is not 'Strange'
        if "comedy" in genres_lower and surreal_cnt == 0:
            s_score -= 0.35

        mood_scores["strange"] = max(0.0, min(1.0, round(s_score, 3)))
        primary_cues["strange"] = s_cues[:4]

        return ContentTagResult(
            mood_scores=mood_scores,
            pace=pace,
            darkness=darkness,
            intensity=intensity,
            primary_cues=primary_cues
        )
