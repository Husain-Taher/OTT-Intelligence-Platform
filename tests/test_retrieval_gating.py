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
def default_taste():
    return UserTasteVector(
        user_id="test_user",
        genres={"Drama": 0.8, "Sci-Fi": 0.7},
        narrative={"character_driven": 0.8},
        emotions={"JOY": 0.5, "WONDER": 0.5},
        pacing={"medium": 0.6},
        international={"US": 0.8, "KR": 0.6},
        preferred_directors={},
        abandoned_patterns={},
        interaction_count=5
    )


def test_hard_mood_gate_filters_under_06(catalog, semantic_engine, default_taste):
    """
    Every candidate passing retrieval for a mood MUST have mood_score >= 0.6.
    """
    generator = CandidateGenerator(semantic_engine)
    moods = ["comforting", "exciting", "emotional", "reflective", "mystery"]

    for m in moods:
        intent = RecommendationIntent(mood=m)
        candidates = generator.generate_candidates(catalog, default_taste, intent)
        assert len(candidates) > 0, f"Expected candidates for mood {m}"

        for item, _ in candidates:
            score = MultiStageRanker.compute_mood_score(item, m)
            assert score >= 0.6, (
                f"Item '{item.title}' failed mood gate for '{m}' with score {score} (< 0.6)"
            )


def test_comforting_gate_strictly_rejects_dark_and_violent(catalog, semantic_engine, default_taste):
    """
    Comforting mood must strictly gate out dark films (Parasite) and violent anime (Demon Slayer).
    """
    generator = CandidateGenerator(semantic_engine)
    intent = RecommendationIntent(mood="comforting")
    candidates = generator.generate_candidates(catalog, default_taste, intent)

    titles = [item.title for item, _ in candidates]
    assert "Parasite" not in titles, "Parasite must never pass comforting hard gate!"
    assert not any("Demon Slayer" in t for t in titles), "Demon Slayer must never pass comforting hard gate!"
    assert not any("Dark" == t for t in titles), "Dark must never pass comforting hard gate!"

    # Comforting candidates should feature wholesome / gentle titles
    assert any("Totoro" in t or "Amélie" in t or "Piku" in t or "PK" in t for t in titles)


def test_hard_genre_gate_strictly_enforced(catalog, semantic_engine, default_taste):
    """
    When specific genres are selected, 100% of generated candidates must belong to those genres.
    """
    generator = CandidateGenerator(semantic_engine)

    # 1. Animation only
    intent_anim = RecommendationIntent(target_genres=["Animation"])
    cand_anim = generator.generate_candidates(catalog, default_taste, intent_anim)
    assert len(cand_anim) > 0
    for item, _ in cand_anim:
        assert any(g.lower() == "animation" for g in item.genres), (
            f"Item '{item.title}' does not have Animation genre: {item.genres}"
        )

    # 2. Horror only
    intent_horror = RecommendationIntent(target_genres=["Horror"])
    cand_horror = generator.generate_candidates(catalog, default_taste, intent_horror)
    assert len(cand_horror) > 0
    for item, _ in cand_horror:
        assert any(g.lower() == "horror" for g in item.genres), (
            f"Item '{item.title}' does not have Horror genre: {item.genres}"
        )


def test_hard_runtime_and_year_and_language_gating(catalog, semantic_engine, default_taste):
    """
    Runtime, year, and language hard constraints must never be breached.
    """
    generator = CandidateGenerator(semantic_engine)

    # Max runtime 100 minutes
    intent_runtime = RecommendationIntent(max_runtime=100)
    cand_rt = generator.generate_candidates(catalog, default_taste, intent_runtime)
    assert len(cand_rt) > 0
    for item, _ in cand_rt:
        assert item.runtime is None or item.runtime <= 100, (
            f"Item '{item.title}' exceeded runtime {item.runtime} > 100"
        )

    # Year range: 2018 - 2023
    intent_year = RecommendationIntent(year_min=2018, year_max=2023)
    cand_yr = generator.generate_candidates(catalog, default_taste, intent_year)
    assert len(cand_yr) > 0
    for item, _ in cand_yr:
        assert 2018 <= item.release_year <= 2023, (
            f"Item '{item.title}' year {item.release_year} outside [2018, 2023]"
        )

    # Language 'ja' (Japanese)
    intent_ja = RecommendationIntent(language="ja")
    cand_ja = generator.generate_candidates(catalog, default_taste, intent_ja)
    assert len(cand_ja) > 0
    for item, _ in cand_ja:
        assert item.original_language == "ja", (
            f"Item '{item.title}' language is {item.original_language}, expected 'ja'"
        )


def test_masterpiece_gate_requires_high_rating_and_votes(catalog, semantic_engine, default_taste):
    """
    Masterpiece gate requires rating >= 8.0 and vote_count >= 1000.
    """
    generator = CandidateGenerator(semantic_engine)
    intent_mp = RecommendationIntent(masterpiece_only=True)
    cand_mp = generator.generate_candidates(catalog, default_taste, intent_mp)

    assert len(cand_mp) > 0
    for item, _ in cand_mp:
        assert item.vote_average >= 8.0, f"'{item.title}' rating {item.vote_average} < 8.0"
        assert item.vote_count >= 1000, f"'{item.title}' vote count {item.vote_count} < 1000"
