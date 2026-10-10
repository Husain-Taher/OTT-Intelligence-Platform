import re
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from app.models.schemas import CanonicalContent, RecommendationIntent, EmotionType
from app.intelligence.vector_index import DenseVectorIndex
from app.intelligence.search_index import TypoTolerantSearchIndex


class SemanticEngine:
    def __init__(self):
        self.vector_index = DenseVectorIndex()
        self.search_index = TypoTolerantSearchIndex()
        self.content_ids: List[str] = []
        self.is_fitted = False

    def build_index(self, items: List[CanonicalContent]):
        if not items:
            return

        self.content_ids = [item.content_id for item in items]
        self.vector_index.index_items(items)
        self.search_index.build_index(items)
        self.is_fitted = True

    def parse_natural_intent(self, query: str) -> RecommendationIntent:
        """
        Parses queries like:
        - 'something like Dark but less confusing'
        - 'Korean thriller with a satisfying ending'
        - '90 minute mystery'
        - 'emotional but not depressing'
        """
        q_low = query.lower()
        intent = RecommendationIntent(query_text=query)

        # Runtime constraint extraction (e.g. "90 minute", "under 2 hours", "120 min")
        runtime_match = re.search(r'(\d{2,3})\s*(?:min|minute)', q_low)
        if runtime_match:
            intent.max_runtime = int(runtime_match.group(1))
        elif "2 hour" in q_low or "120" in q_low:
            intent.max_runtime = 120
        elif "90" in q_low:
            intent.max_runtime = 95

        # Region intent
        if "korean" in q_low or "korea" in q_low:
            intent.preferred_regions.append("KR")
        if "japanese" in q_low or "japan" in q_low:
            intent.preferred_regions.append("JP")
        if "french" in q_low or "france" in q_low:
            intent.preferred_regions.append("FR")
        if "german" in q_low or "germany" in q_low:
            intent.preferred_regions.append("DE")
        if "indian" in q_low or "india" in q_low:
            intent.preferred_regions.append("IN")

        # Mood and Genre detection
        if any(w in q_low for w in ["love", "romance", "romantic", "relationship", "couple"]):
            intent.mood = "romance"
            intent.target_genres.append("Romance")
        elif any(w in q_low for w in ["emotional", "feel something", "cry", "poignant", "heartwarming"]):
            intent.mood = "emotional"
            intent.target_genres.append("Drama")
        elif any(w in q_low for w in ["mystery", "whodunit", "puzzle", "secrets"]):
            intent.mood = "mystery"
            intent.target_genres.append("Mystery")
        elif any(w in q_low for w in ["think", "intellectual", "philosophical", "mind-bending"]):
            intent.mood = "reflective"
            intent.target_genres.append("Science Fiction")
        elif any(w in q_low for w in ["comfort", "relax", "feel-good", "light", "funny", "comedy"]):
            intent.mood = "comforting"
            intent.target_genres.append("Comedy")
        elif any(w in q_low for w in ["exciting", "action", "thrill", "adrenaline"]):
            intent.mood = "exciting"
            intent.target_genres.append("Action")
        elif any(w in q_low for w in ["strange", "weird", "unusual", "surreal"]):
            intent.mood = "strange"

        # Explicit genre checks
        if "thriller" in q_low and "Thriller" not in intent.target_genres:
            intent.target_genres.append("Thriller")
        if ("sci-fi" in q_low or "science fiction" in q_low) and "Science Fiction" not in intent.target_genres:
            intent.target_genres.append("Science Fiction")
        if "horror" in q_low and "Horror" not in intent.target_genres:
            intent.target_genres.append("Horror")
        if ("animation" in q_low or "anime" in q_low) and "Animation" not in intent.target_genres:
            intent.target_genres.append("Animation")
        if "documentary" in q_low and "Documentary" not in intent.target_genres:
            intent.target_genres.append("Documentary")

        # Negative constraints (e.g. "not depressing", "less confusing", "less violent")
        if "not depressing" in q_low or "less sad" in q_low:
            intent.avoid_tags.append("depression")
        if "less confusing" in q_low or "less complicated" in q_low:
            intent.avoid_tags.append("high_complexity")
        if "not violent" in q_low or "less violent" in q_low:
            intent.avoid_tags.append("extreme_violence")

        # Novelty / Adventurousness
        if "outside my taste" in q_low or "surprise me" in q_low or "unexpected" in q_low:
            intent.novelty = 0.9
        elif "familiar" in q_low or "like usual" in q_low:
            intent.novelty = 0.2

        return intent

    def search_semantic(
        self,
        query: str,
        items_map: Dict[str, CanonicalContent],
        top_k: int = 20
    ) -> List[Tuple[CanonicalContent, float]]:
        """
        Meaning-aware dense vector search using BGE-small embeddings.
        Replaces legacy TF-IDF word overlap model.
        """
        if not self.is_fitted:
            return []

        hits = self.vector_index.search(query, top_k=top_k)
        results = []
        for cid, score in hits:
            if cid in items_map and score > 0.05:
                results.append((items_map[cid], round(score, 3)))
        return results

    def find_similar_to_title(
        self,
        source_id: str,
        items_map: Dict[str, CanonicalContent],
        top_k: int = 10
    ) -> List[Tuple[CanonicalContent, float]]:
        """
        Finds conceptually similar films in the 384-dimensional semantic space.
        """
        if not self.is_fitted:
            return []

        hits = self.vector_index.find_similar(source_id, top_k=top_k)
        results = []
        for cid, score in hits:
            if cid in items_map:
                results.append((items_map[cid], round(score, 3)))
        return results

    def search_keyword(
        self,
        query: str,
        genres: Optional[List[str]] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        min_rating: Optional[float] = None,
        language: Optional[str] = None,
        max_runtime: Optional[int] = None,
        top_k: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Typo-tolerant fuzzy keyword search across title, directors, cast, and keywords.
        """
        return self.search_index.search(
            query=query,
            genres=genres,
            year_min=year_min,
            year_max=year_max,
            min_rating=min_rating,
            language=language,
            max_runtime=max_runtime,
            top_k=top_k
        )
