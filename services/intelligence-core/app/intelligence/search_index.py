"""
Typo-Tolerant Search Index for OTT Intelligence Platform.
Enables fast fuzzy search with edit-distance tolerance across:
- Titles (and original titles)
- Directors
- Actors & Cast
- Keywords

Supports multi-faceted filtering by genre, release year range,
rating thresholds, language, and runtime limits.
"""
import re
from typing import List, Dict, Any, Tuple, Optional, Set
from app.models.schemas import CanonicalContent


def damerau_levenshtein_distance(s1: str, s2: str) -> int:
    """Computes Damerau-Levenshtein distance between two strings with transposition support."""
    d = {}
    len1 = len(s1)
    len2 = len(s2)
    for i in range(-1, len1 + 1):
        d[(i, -1)] = i + 1
    for j in range(-1, len2 + 1):
        d[(-1, j)] = j + 1

    for i in range(len1):
        for j in range(len2):
            cost = 0 if s1[i] == s2[j] else 1
            d[(i, j)] = min(
                d[(i - 1, j)] + 1,        # deletion
                d[(i, j - 1)] + 1,        # insertion
                d[(i - 1, j - 1)] + cost  # substitution
            )
            if i > 0 and j > 0 and s1[i] == s2[j - 1] and s1[i - 1] == s2[j]:
                d[(i, j)] = min(d[(i, j)], d[(i - 2, j - 2)] + cost) # transposition

    return d[(len1 - 1, len2 - 1)]


class SearchHit:
    def __init__(self, item: CanonicalContent, score: float, match_reason: str):
        self.item = item
        self.score = score
        self.match_reason = match_reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.item,
            "score": round(self.score, 3),
            "match_reason": self.match_reason
        }


class TypoTolerantSearchIndex:
    def __init__(self):
        self.items: List[CanonicalContent] = []
        self.items_by_id: Dict[str, CanonicalContent] = {}

    def build_index(self, items: List[CanonicalContent]):
        self.items = list(items)
        self.items_by_id = {it.content_id: it for it in items}

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r'[^\w\s]', '', text.lower()).strip()

    def search(
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
        Executes typo-tolerant multi-field search with faceted filtering.
        """
        q_norm = self._normalize(query)
        if not q_norm:
            return []

        q_tokens = q_norm.split()
        target_genres_lower = [g.lower() for g in (genres or [])]
        hits: List[SearchHit] = []

        for item in self.items:
            # 1. Facet Filtering
            genres_lower = [g.lower() for g in item.genres]
            if target_genres_lower and not any(tg in genres_lower for tg in target_genres_lower):
                continue
            if year_min and item.release_year and item.release_year < year_min:
                continue
            if year_max and item.release_year and item.release_year > year_max:
                continue
            if min_rating and item.vote_average < min_rating:
                continue
            if language and item.original_language.lower() != language.lower():
                continue
            if max_runtime and item.runtime and item.runtime > max_runtime:
                continue

            # 2. Text Match Scoring
            title_norm = self._normalize(item.title)
            orig_title_norm = self._normalize(item.original_title or "")
            directors_norm = [self._normalize(d) for d in item.directors]
            cast_norm = [self._normalize(c) for c in item.cast]
            keywords_norm = [self._normalize(k) for k in (item.keywords or [])]

            best_field_score = 0.0
            best_reason = ""

            # Check Title
            if q_norm == title_norm or q_norm == orig_title_norm:
                best_field_score = 1.0
                best_reason = f"Exact title match: {item.title}"
            elif title_norm.startswith(q_norm) or any(t.startswith(q_norm) for t in title_norm.split()):
                best_field_score = 0.90
                best_reason = f"Title prefix match: {item.title}"
            elif q_norm in title_norm:
                best_field_score = 0.85
                best_reason = f"Title contains '{query}'"
            else:
                # Fuzzy Title Match (Damerau-Levenshtein)
                # Compare full title or tokens if query length is sufficient
                if len(q_norm) >= 4:
                    dist = damerau_levenshtein_distance(q_norm, title_norm)
                    if dist == 1:
                        best_field_score = max(best_field_score, 0.82)
                        best_reason = f"Fuzzy title match (1 typo): {item.title}"
                    elif dist == 2 and len(q_norm) >= 6:
                        best_field_score = max(best_field_score, 0.72)
                        best_reason = f"Fuzzy title match (2 typos): {item.title}"
                    else:
                        # Check each word of title against query
                        for tw in title_norm.split():
                            if len(tw) >= 4:
                                w_dist = damerau_levenshtein_distance(q_norm, tw)
                                if w_dist <= 1:
                                    best_field_score = max(best_field_score, 0.75)
                                    best_reason = f"Fuzzy title token match: {tw}"
                                    break

            # Check Directors
            for dir_name, raw_d in zip(directors_norm, item.directors):
                if q_norm in dir_name or any(t in dir_name.split() for t in q_tokens):
                    score = 0.85 if q_norm == dir_name else 0.78
                    if score > best_field_score:
                        best_field_score = score
                        best_reason = f"Directed by {raw_d}"
                elif len(q_norm) >= 4:
                    for dw in dir_name.split():
                        if len(dw) >= 4 and damerau_levenshtein_distance(q_norm, dw) <= 1:
                            if 0.72 > best_field_score:
                                best_field_score = 0.72
                                best_reason = f"Fuzzy director match: {raw_d}"

            # Check Cast
            for cast_name, raw_c in zip(cast_norm[:6], item.cast[:6]):
                if q_norm in cast_name or any(t in cast_name.split() for t in q_tokens):
                    score = 0.80 if q_norm == cast_name else 0.72
                    if score > best_field_score:
                        best_field_score = score
                        best_reason = f"Starring {raw_c}"
                elif len(q_norm) >= 4:
                    for cw in cast_name.split():
                        if len(cw) >= 4 and damerau_levenshtein_distance(q_norm, cw) <= 1:
                            if 0.68 > best_field_score:
                                best_field_score = 0.68
                                best_reason = f"Fuzzy actor match: {raw_c}"

            # Check Keywords
            for kw in keywords_norm:
                if q_norm == kw or (len(q_norm) >= 4 and q_norm in kw):
                    if 0.65 > best_field_score:
                        best_field_score = 0.65
                        best_reason = f"Thematic keyword: {kw}"

            if best_field_score > 0.0:
                # Bayesian quality multiplier (vote average + count)
                quality_bonus = min(0.12, (item.vote_average - 6.0) * 0.04) if item.vote_average >= 6.0 else 0.0
                final_score = min(1.0, best_field_score + quality_bonus)
                hits.append(SearchHit(item=item, score=final_score, match_reason=best_reason))

        hits.sort(key=lambda h: h.score, reverse=True)
        return [h.to_dict() for h in hits[:top_k]]
