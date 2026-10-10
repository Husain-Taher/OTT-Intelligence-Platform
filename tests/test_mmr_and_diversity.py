import os, sys
import pytest
from typing import Set

ROOT = os.path.join(os.path.dirname(__file__), "..", "services", "intelligence-core")
sys.path.insert(0, os.path.abspath(ROOT))

from app.models.schemas import CanonicalContent, ContentType, RecommendationIntent, UserTasteVector
from app.intelligence.semantic_engine import SemanticEngine
from app.recommender.candidate_generators import CandidateGenerator
from app.recommender.ranker import MultiStageRanker
from app.db.database import get_all_content, log_shown_history, get_recent_shown_counts, delete_user_data


@pytest.fixture(scope="module")
def catalog():
    return get_all_content()


@pytest.fixture(scope="module")
def semantic_engine(catalog):
    engine = SemanticEngine()
    engine.build_index(catalog)
    return engine


def test_mmr_diversifies_and_caps_directors(catalog, semantic_engine):
    """
    Maximal Marginal Relevance (MMR) must enforce:
    1. Maximum 1 film per director in any recommended top-5 set.
    2. High cosine distinctness across recommended candidates.
    """
    generator = CandidateGenerator(semantic_engine)
    taste = UserTasteVector(user_id="dir_cap_user", interaction_count=0)

    for m in ["comforting", "exciting", "reflective", "mystery"]:
        intent = RecommendationIntent(mood=m)
        cands = generator.generate_candidates(catalog, taste, intent)
        ranked = MultiStageRanker.rank_and_diversify(cands, taste, intent, top_n=5)
        assert len(ranked) == 5

        # Check director uniqueness
        directors_seen = []
        for item, _, _, _, _, _, _ in ranked:
            for d in item.directors:
                assert d not in directors_seen, f"Director '{d}' appeared more than once in top-5 for mood '{m}'!"
                directors_seen.append(d)


def test_mmr_franchise_capping(catalog, semantic_engine):
    """
    Ensures no franchise (e.g. Spider-Man, Batman, etc.) occupies multiple slots in a recommendation set.
    """
    generator = CandidateGenerator(semantic_engine)
    taste = UserTasteVector(user_id="franchise_test_user", interaction_count=5)
    intent = RecommendationIntent(target_genres=["Action"], mood="exciting")

    cands = generator.generate_candidates(catalog, taste, intent)
    ranked = MultiStageRanker.rank_and_diversify(cands, taste, intent, top_n=5)
    assert len(ranked) == 5

    titles = [r[0].title.lower() for r in ranked]
    spider_man_count = sum(1 for t in titles if "spider-man" in t)
    assert spider_man_count <= 1, "Spider-Man franchise appeared more than once in top 5!"


def test_session_recency_penalty_eliminates_repeats(catalog, semantic_engine):
    """
    Simulates consecutive rolls/sessions: items shown in Session 1 should be penalized,
    yielding fresh picks in Session 2 (< 20% overlap).
    """
    user_id = "test_recency_user_xyz"
    delete_user_data(user_id)

    generator = CandidateGenerator(semantic_engine)
    taste = UserTasteVector(user_id=user_id, interaction_count=0)
    intent = RecommendationIntent(mood="comforting")

    cands = generator.generate_candidates(catalog, taste, intent)

    # Session 1: initial roll
    s1 = MultiStageRanker.rank_and_diversify(cands, taste, intent, top_n=5)
    s1_ids = [r[0].content_id for r in s1]
    assert len(s1_ids) == 5
    log_shown_history(user_id, s1_ids, mood="comforting")

    # Session 2: next roll with recency history
    shown_counts = get_recent_shown_counts(user_id, limit=50)
    s2 = MultiStageRanker.rank_and_diversify(cands, taste, intent, top_n=5, shown_counts=shown_counts)
    s2_ids = [r[0].content_id for r in s2]
    assert len(s2_ids) == 5

    overlap = set(s1_ids).intersection(set(s2_ids))
    overlap_pct = (len(overlap) / 5.0) * 100
    assert overlap_pct <= 20.0, f"Repeat overlap {overlap_pct}% exceeded 20% target! Overlap items: {overlap}"

    delete_user_data(user_id)
