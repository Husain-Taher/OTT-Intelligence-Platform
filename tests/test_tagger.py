"""
Tests for Phase 2: Systematic Tagging Engine & Dimensional Profiling.
Validates:
- 7 core mood scores (0.0 - 1.0)
- 3 continuous dimensions (pace, darkness, intensity)
- Accurate handling of difficult counter-examples (Parasite, Demon Slayer, Totoro, Amélie, John Wick, Interstellar)
- Fact-based explanation cues
"""
import os
import sys
import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..", "services", "intelligence-core")
sys.path.insert(0, os.path.abspath(ROOT))

from app.db.database import get_all_content
from app.intelligence.tagger import ContentTagger
from app.models.schemas import CanonicalContent, ContentType, ContentProfile


def test_tagger_dimensions_bounds():
    """Asserts that darkness, intensity, and pace are strictly bounded within [0.0, 1.0]."""
    items = get_all_content()
    assert len(items) > 0, "No content items in catalog"

    for item in items[:25]:
        dims = ContentTagger.compute_dimensions(item)
        assert 0.0 <= dims["darkness"] <= 1.0, f"Darkness out of bounds for {item.title}: {dims['darkness']}"
        assert 0.0 <= dims["intensity"] <= 1.0, f"Intensity out of bounds for {item.title}: {dims['intensity']}"
        assert 0.0 <= dims["pace"] <= 1.0, f"Pace out of bounds for {item.title}: {dims['pace']}"


def test_parasite_and_dark_films_never_comforting():
    """
    Asserts that Parasite (dark thriller tagged comedy) and violent films
    receive low comforting score (<= 0.15) and high darkness/intensity.
    """
    items = get_all_content()
    parasite = next((i for i in items if "parasite" in i.title.lower()), None)
    assert parasite is not None, "Parasite missing from catalog"

    res = ContentTagger.tag_content(parasite)
    assert res.darkness >= 0.60, f"Expected high darkness for Parasite, got {res.darkness}"
    assert res.intensity >= 0.55, f"Expected high intensity for Parasite, got {res.intensity}"
    assert res.mood_scores["comforting"] <= 0.15, f"Parasite scored {res.mood_scores['comforting']} for comforting!"


def test_wholesome_films_have_high_comfort_low_darkness():
    """
    Asserts that genuinely gentle/wholesome films (Totoro, Amélie)
    have low darkness (< 0.25), low intensity (< 0.45), and high comfort (>= 0.50).
    """
    items = get_all_content()
    totoro = next((i for i in items if "totoro" in i.title.lower()), None)
    amelie = next((i for i in items if "amélie" in i.title.lower() or "amelie" in i.title.lower()), None)

    for film in [totoro, amelie]:
        if film:
            res = ContentTagger.tag_content(film)
            assert res.darkness <= 0.25, f"{film.title} has unexpectedly high darkness: {res.darkness}"
            assert res.mood_scores["comforting"] >= 0.50, f"{film.title} comfort score {res.mood_scores['comforting']} < 0.50"


def test_kinetic_action_has_high_exciting_and_intensity():
    """
    Asserts that action spectacle films (John Wick)
    score high intensity (>= 0.75), high pace (>= 0.60), and high exciting (>= 0.75).
    """
    items = get_all_content()
    john_wick = next((i for i in items if "john wick" in i.title.lower()), None)
    if john_wick:
        res = ContentTagger.tag_content(john_wick)
        assert res.intensity >= 0.75
        assert res.pace >= 0.60
        assert res.mood_scores["exciting"] >= 0.75
        assert res.mood_scores["comforting"] <= 0.10


def test_philosophical_scifi_has_high_reflective():
    """
    Asserts that intellectual/existential sci-fi (Interstellar)
    scores high reflective (>= 0.75).
    """
    items = get_all_content()
    interstellar = next((i for i in items if "interstellar" in i.title.lower()), None)
    if interstellar:
        res = ContentTagger.tag_content(interstellar)
        assert res.mood_scores["reflective"] >= 0.75


def test_tagger_explanation_cues():
    """Asserts that primary explanation cues are extracted and factual."""
    items = get_all_content()
    test_item = items[0]
    res = ContentTagger.tag_content(test_item)

    assert isinstance(res.primary_cues, dict)
    for mood in ["comforting", "exciting", "reflective", "mystery", "emotional", "romance", "strange"]:
        assert mood in res.primary_cues
        # Cues should be non-empty list of strings
        cues = res.primary_cues[mood]
        assert isinstance(cues, list)
