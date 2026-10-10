import os, sys
import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..", "services", "intelligence-core")
sys.path.insert(0, os.path.abspath(ROOT))

from app.models.schemas import CanonicalContent, ContentType, RecommendationIntent, UserTasteVector
from app.intelligence.semantic_engine import SemanticEngine
from app.intelligence.taste_engine import TasteEngine
from app.recommender.candidate_generators import CandidateGenerator
from app.recommender.ranker import MultiStageRanker
from app.db.database import get_all_content, save_user_taste, get_user_taste, delete_user_data, add_mood_affinity, get_mood_affinity


@pytest.fixture(scope="module")
def catalog():
    return get_all_content()


@pytest.fixture(scope="module")
def semantic_engine(catalog):
    engine = SemanticEngine()
    engine.build_index(catalog)
    return engine


def test_fact_grounded_explanations(catalog, semantic_engine):
    """
    Validates Phase 7 requirement:
    Explanations must never be hallucinated; they must be constructed strictly
    from database facts: real taglines, verified keywords, audience review excerpts,
    directors, and content feeling cues.
    """
    generator = CandidateGenerator(semantic_engine)
    taste = UserTasteVector(user_id="fact_user", interaction_count=5)
    intent = RecommendationIntent(mood="comforting")

    cands = generator.generate_candidates(catalog, taste, intent)
    ranked = MultiStageRanker.rank_and_diversify(cands, taste, intent, top_n=5)
    assert len(ranked) == 5

    for item, score, pct, breakdown, reasons, diffs, note in ranked:
        assert len(reasons) > 0, f"Expected fact-grounded reasons for '{item.title}'"

        # Check that reasons reflect verified fields
        reasons_text = " ".join(reasons).lower()
        has_verified_fact = (
            any(d.lower() in reasons_text for d in item.directors) or
            (item.tagline and any(w.lower() in reasons_text for w in item.tagline.split()[:4] if len(w) > 4)) or
            any(g.lower() in reasons_text for g in item.genres) or
            any(k.lower() in reasons_text for k in (item.keywords or [])[:3]) or
            "feeling:" in reasons_text or
            "audience note:" in reasons_text or
            "genre match" in reasons_text
        )
        assert has_verified_fact, f"Reasons for '{item.title}' did not contain verified facts: {reasons}"


def test_continuous_learning_and_mood_adaptation(catalog):
    """
    Validates continuous learning:
    Every reaction event (LIKE, WATCH_COMPLETE, REWATCH, SAVE) updates
    both user taste vector and per-mood genre affinities.
    """
    user_id = "test_learning_user_123"
    delete_user_data(user_id)

    # Initial blank taste
    taste = TasteEngine.get_blank_taste(user_id)
    assert taste.interaction_count == 0

    # User watches and completes an Animation/Family title
    totoro = next((it for it in catalog if "Totoro" in it.title), None)
    assert totoro is not None

    # Learn from event
    updated_taste = TasteEngine.update_taste_with_event(taste, totoro, "WATCH_COMPLETE")
    assert updated_taste.interaction_count == 1
    assert updated_taste.genres.get("Animation", 0) > 0.5

    # Add mood affinity signal
    add_mood_affinity(user_id, "comforting", totoro.genres, signal=1.0)
    affinities = get_mood_affinity(user_id)
    assert "comforting" in affinities
    assert "Animation" in affinities["comforting"]
    assert affinities["comforting"]["Animation"]["weight"] > 0

    delete_user_data(user_id)
