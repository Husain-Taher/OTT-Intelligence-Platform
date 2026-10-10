import re
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.models.schemas import CanonicalContent, RecommendationIntent, EmotionType

class SemanticEngine:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=5000
        )
        self.content_ids: List[str] = []
        self.tfidf_matrix = None
        self.is_fitted = False

    def build_index(self, items: List[CanonicalContent]):
        if not items:
            return
        
        self.content_ids = [item.content_id for item in items]
        documents = []
        for item in items:
            # Rich document incorporating title, overview, genres, keywords, directors, cast, and narrative attributes
            prof = item.profile
            doc_parts = [
                item.title,
                item.original_title or "",
                item.overview,
                " ".join(item.genres),
                " ".join(item.keywords),
                " ".join(item.directors),
                " ".join(item.cast[:4]),
                f"language_{item.original_language}",
                " ".join(f"country_{c}" for c in item.origin_countries),
            ]
            if prof:
                # Add dominant emotions and pacing tags
                top_emotions = [k for k, v in prof.emotions.items() if v >= 0.4]
                doc_parts.append(" ".join(top_emotions))
                pacing_tag = max(prof.pacing.items(), key=lambda x: x[1])[0]
                doc_parts.append(f"pacing_{pacing_tag}")
                if prof.narrative_complexity >= 0.7:
                    doc_parts.append("complex_narrative non_linear")
                if prof.mystery >= 0.7:
                    doc_parts.append("deep_mystery whodunit")
                if prof.philosophical_depth >= 0.7:
                    doc_parts.append("philosophical existential")
            documents.append(" ".join(doc_parts))

        self.tfidf_matrix = self.vectorizer.fit_transform(documents)
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
        if "sci-fi" in q_low or "science fiction" in q_low and "Science Fiction" not in intent.target_genres:
            intent.target_genres.append("Science Fiction")
        if "horror" in q_low and "Horror" not in intent.target_genres:
            intent.target_genres.append("Horror")
        if "animation" in q_low or "anime" in q_low and "Animation" not in intent.target_genres:
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
        if not self.is_fitted or self.tfidf_matrix is None:
            return []

        query_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Rank indices
        top_indices = np.argsort(-sims)[:top_k]
        results = []
        for idx in top_indices:
            score = float(sims[idx])
            if score > 0.01:
                cid = self.content_ids[idx]
                if cid in items_map:
                    results.append((items_map[cid], round(score, 3)))
        return results

    def find_similar_to_title(
        self,
        source_id: str,
        items_map: Dict[str, CanonicalContent],
        top_k: int = 10
    ) -> List[Tuple[CanonicalContent, float]]:
        if not self.is_fitted or source_id not in self.content_ids:
            return []

        idx = self.content_ids.index(source_id)
        source_vec = self.tfidf_matrix[idx]
        sims = cosine_similarity(source_vec, self.tfidf_matrix).flatten()

        top_indices = np.argsort(-sims)
        results = []
        for i in top_indices:
            cid = self.content_ids[i]
            if cid != source_id and cid in items_map:
                results.append((items_map[cid], round(float(sims[i]), 3)))
                if len(results) >= top_k:
                    break
        return results
