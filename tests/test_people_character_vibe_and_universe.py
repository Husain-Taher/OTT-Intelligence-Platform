import os, sys
import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..", "services", "intelligence-core")
sys.path.insert(0, os.path.abspath(ROOT))

from app.api.routes import match_character_vibe, get_taste_universe
from app.auth.auth0 import AuthUser


def test_character_vibe_endpoint_finds_matching_psychological_resonance():
    test_user = AuthUser(user_id="test_vibe_user")
    
    # 1. Search for a complex character performance
    res = match_character_vibe(
        actor_name="Cillian Murphy",
        character_name="J. Robert Oppenheimer",
        reference_title="Oppenheimer",
        user=test_user
    )
    
    assert res["actor_name"] == "Cillian Murphy"
    assert res["count"] > 0
    assert len(res["results"]) > 0
    
    # Verify top matched title has vibe scores and reasons
    top_pick = res["results"][0]
    assert "character_vibe_score" in top_pick
    assert "personal_match_percentage" in top_pick
    assert len(top_pick["vibe_reasons"]) > 0
    assert top_pick["character_vibe_score"] > 0.0


def test_frontier_discovery_in_taste_universe():
    test_user = AuthUser(user_id="test_frontier_user")
    
    universe = get_taste_universe(user=test_user)
    assert "clusters" in universe
    assert len(universe["clusters"]) == 6
    assert "frontier_titles" in universe
    assert len(universe["frontier_titles"]) > 0
    
    # Verify frontier title is high quality
    frontier_item = universe["frontier_titles"][0]
    assert frontier_item["content"].vote_average >= 8.0
    assert "discovery_reason" in frontier_item
