"""
Mood catalog: single source of truth for mood ids, aliases and the genres that
tend to serve each mood. The web app mirrors the ids (palette/copy live there).
"""
from typing import Dict, List, Optional

MOODS: Dict[str, Dict] = {
    "comforting": {
        "label": "Comforting",
        "tagline": "Warm, easy, nothing that bites.",
        "energy": "low",
        "genres": ["Comedy", "Animation", "Family", "Romance"],
    },
    "emotional": {
        "label": "Emotional",
        "tagline": "Something that leaves a mark.",
        "energy": "low",
        "genres": ["Drama", "Romance", "History"],
    },
    "reflective": {
        "label": "Reflective",
        "tagline": "Big ideas to sit with afterwards.",
        "energy": "medium",
        "genres": ["Science Fiction", "Drama", "Mystery"],
    },
    "mystery": {
        "label": "Mystery",
        "tagline": "Clues, twists, a reveal worth waiting for.",
        "energy": "medium",
        "genres": ["Mystery", "Thriller", "Crime"],
    },
    "exciting": {
        "label": "Exciting",
        "tagline": "Pulse up, phone down.",
        "energy": "high",
        "genres": ["Action", "Adventure", "Thriller"],
    },
    "romance": {
        "label": "Romantic",
        "tagline": "Butterflies, slow glances, big feelings.",
        "energy": "low",
        "genres": ["Romance", "Drama", "Comedy"],
    },
    "strange": {
        "label": "Strange",
        "tagline": "Surprise me. Take me somewhere odd.",
        "energy": "medium",
        "genres": ["Fantasy", "Science Fiction", "Horror", "Mystery"],
    },
}

ALIASES = {
    "wholesome": "comforting", "light": "comforting", "cozy": "comforting",
    "adrenaline": "exciting", "action": "exciting",
    "poignant": "emotional", "feel something": "emotional",
    "intellectual": "reflective", "philosophical": "reflective",
    "romantic": "romance", "love": "romance",
    "whodunit": "mystery", "puzzle": "mystery",
    "weird": "strange", "surprise": "strange",
}


def normalize_mood(value: Optional[str]) -> Optional[str]:
    """Maps free text / aliases to a canonical mood id, or None if unknown."""
    if not value:
        return None
    v = value.strip().lower()
    if v in MOODS:
        return v
    return ALIASES.get(v)


def catalog(available_genres: List[str]) -> List[Dict]:
    """Moods with genre hints limited to genres that really exist in the catalog."""
    have = {g.lower(): g for g in available_genres}
    out = []
    for mood_id, m in MOODS.items():
        hints = [have[g.lower()] for g in m["genres"] if g.lower() in have]
        out.append({"id": mood_id, "label": m["label"], "tagline": m["tagline"],
                    "energy": m["energy"], "genres": hints})
    return out
