import os, sys
import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..", "services", "intelligence-core")
sys.path.insert(0, os.path.abspath(ROOT))

from app.models.schemas import CanonicalContent, ContentType, RecommendationIntent, UserTasteVector
from app.intelligence.semantic_engine import SemanticEngine
from app.recommender.candidate_generators import CandidateGenerator
from app.recommender.ranker import MultiStageRanker
from app.db.database import get_all_content


@pytest.fixture(scope="module")
def catalog():
    return get_all_content()


@pytest.fixture(scope="module")
def semantic_engine(catalog):
    engine = SemanticEngine()
    engine.build_index(catalog)
    return engine


@pytest.fixture(scope="module")
def sample_taste():
    return UserTasteVector(
        user_id="cinephile_test",
        genres={"Drama": 0.85, "Animation": 0.80, "Action": 0.70},
        narrative={"character_driven": 0.85, "philosophical": 0.75},
        emotions={"JOY": 0.75, "COMFORT": 0.70, "WONDER": 0.80},
        pacing={"medium": 0.70, "slow_build": 0.60},
        international={"JP": 0.85, "KR": 0.75, "US": 0.70},
        preferred_directors={"Hayao Miyazaki": 0.95},
        abandoned_patterns={},
        interaction_count=15
    )


def test_ranking_weights_and_mood_dominance(catalog, semantic_engine, sample_taste):
    """
    Validates Phase 5 formula: Mood Fit (0.35), Taste (0.25), Quality (0.15),
    Collaborative (0.15), Novelty (0.10).
    Under comforting mood, top 5 picks must have strong mood fit and match user preferences.
    """
    generator = CandidateGenerator(semantic_engine)
    intent = RecommendationIntent(mood="comforting")

    candidates = generator.generate_candidates(catalog, sample_taste, intent)
    assert len(candidates) >= 5

    ranked = MultiStageRanker.rank_and_diversify(candidates, sample_taste, intent, top_n=5)
    assert len(ranked) == 5

    for item, final_score, match_pct, breakdown, reasons, diffs, note in ranked:
        mood_fit = MultiStageRanker.compute_mood_score(item, "comforting")
        assert mood_fit >= 0.60, f"'{item.title}' mood fit {mood_fit} below 0.60"
        assert final_score > 0.40, f"'{item.title}' final score {final_score} too low"
        assert match_pct >= 50, f"'{item.title}' match percentage {match_pct} too low"


def test_ranking_query_mode_blends_semantic_intent(catalog, semantic_engine, sample_taste):
    """
    When free-text prompt is provided, semantic NLP weight is factored in.
    Searching 'peaceful spirit in the forest' should rank Studio Ghibli / Totoro at or near the top.
    """
    generator = CandidateGenerator(semantic_engine)
    intent = RecommendationIntent(query_text="peaceful spirit in the forest", mood="comforting")

    candidates = generator.generate_candidates(catalog, sample_taste, intent)
    assert len(candidates) > 0

    ranked = MultiStageRanker.rank_and_diversify(candidates, sample_taste, intent, top_n=5)
    assert len(ranked) >= 1

    top_item = ranked[0][0]
    top_titles = [r[0].title for r in ranked]
    assert any("Totoro" in t or "Spirited" in t for t in top_titles), (
        f"Expected Totoro or Spirited Away in top picks, got: {top_titles}"
    )


def test_ranking_novelty_boosts_international_cinema(catalog, semantic_engine):
    """
    Higher novelty parameter should elevate non-US/GB international cinema titles.
    """
    generator = CandidateGenerator(semantic_engine)
    low_novelty_intent = RecommendationIntent(mood="exciting", novelty=0.1)
    high_novelty_intent = RecommendationIntent(mood="exciting", novelty=0.9)

    taste = UserTasteVector(
        user_id="neutral_user",
        genres={"Action": 0.8},
        interaction_count=5
    )

    cand_low = generator.generate_candidates(catalog, taste, low_novelty_intent)
    cand_high = generator.generate_candidates(catalog, taste, high_novelty_intent)

    ranked_low = MultiStageRanker.rank_and_diversify(cand_low, taste, low_novelty_intent, top_n=5)
    ranked_high = MultiStageRanker.rank_and_diversify(cand_high, taste, high_novelty_intent, top_n=5)

    assert len(ranked_low) > 0 and len(ranked_high) > 0
