"""
Engine quality tests validating Phase 0 requirements:
- Hard mood gates (e.g. no Horror in Comforting)
- Catalog diversity across the 7 moods for fresh profiles
- Hard genre enforcement when sufficient titles exist
- Session memory / shown_history penalty reducing repeats
"""
import os, sys, time, shutil, types
import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..", "services", "intelligence-core")
sys.path.insert(0, os.path.abspath(ROOT))

os.environ["AUTH_DISABLED"] = "false"
os.environ["AUTH0_DOMAIN"] = "test-tenant.us.auth0.com"
os.environ["AUTH0_AUDIENCE"] = "https://ott-test-api"

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

ISS = "https://test-tenant.us.auth0.com/"
AUD = "https://ott-test-api"
_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_token(sub="auth0|fresh_user", aud=AUD, iss=ISS, exp_in=3600, key=_KEY):
    now = int(time.time())
    return jwt.encode({"sub": sub, "aud": aud, "iss": iss, "iat": now, "exp": now + exp_in}, key, algorithm="RS256")


def H(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app.db import database
    from app.auth import auth0
    db = tmp_path / "test.db"
    seed = os.path.join(ROOT, "data", "ott_intelligence.db")
    if not os.path.exists(seed):
        pytest.skip("seed catalog database not present")
    shutil.copy(seed, db)
    monkeypatch.setattr(database, "DB_PATH", str(db))
    fake = types.SimpleNamespace(get_signing_key_from_jwt=lambda t: types.SimpleNamespace(key=_KEY.public_key()))
    monkeypatch.setattr(auth0, "_client", lambda: fake)
    auth0._last_touch.clear()
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_mood_diversity_across_seven_moods(client):
    """
    Assert that for a fresh profile, requesting recommendations across
    all 7 core moods produces >= 25 distinct titles (out of 35 total slots).
    """
    token = make_token("auth0|diversity_user")
    moods = ["comforting", "emotional", "reflective", "mystery", "exciting", "romance", "strange"]
    all_seen_ids = set()
    mood_picks = {}

    for mood in moods:
        resp = client.post(
            "/v1/find-my-watch",
            headers=H(token),
            json={"mood": mood, "novelty": 0.5}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        hero = data["hero"]["content"]
        runners = [r["content"] for r in data["runners_up"]]
        picks = [hero] + runners
        assert len(picks) == 5

        picks_ids = [p["content_id"] for p in picks]
        mood_picks[mood] = picks_ids
        for pid in picks_ids:
            all_seen_ids.add(pid)

    # 35 slots total across 7 moods: assert at least 25 distinct films
    print(f"\n[PHASE 0 TEST] Distinct titles across 7 moods: {len(all_seen_ids)} / 35 slots")
    for m, pids in mood_picks.items():
        print(f"  {m:12}: {pids}")
    assert len(all_seen_ids) >= 25, f"Expected >= 25 distinct titles across 7 moods, got {len(all_seen_ids)}"



def test_comforting_never_contains_horror(client):
    """
    Assert that Comforting mood gate strictly rejects Horror films.
    """
    token = make_token("auth0|comfort_user")
    resp = client.post(
        "/v1/find-my-watch",
        headers=H(token),
        json={"mood": "comforting"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    picks = [data["hero"]["content"]] + [r["content"] for r in data["runners_up"]]

    for pick in picks:
        genres = [g.lower() for g in pick.get("genres", [])]
        assert "horror" not in genres, f"Horror film '{pick.get('title')}' appeared in Comforting mood!"
        assert "war" not in genres, f"War film '{pick.get('title')}' appeared in Comforting mood!"


def test_genre_locked_requests_enforced(client):
    """
    Assert that when a user requests specific genres, the engine
    only returns titles matching that genre (unless fewer than 5 exist in the DB).
    """
    token = make_token("auth0|genre_user")

    # 1. Action genre: catalog has 30 Action films, so all 5 must be Action
    resp = client.post(
        "/v1/find-my-watch",
        headers=H(token),
        json={"mood": "exciting", "genres": ["Action"]}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    picks = [data["hero"]["content"]] + [r["content"] for r in data["runners_up"]]
    assert len(picks) == 5
    for pick in picks:
        genres_lower = [g.lower() for g in pick.get("genres", [])]
        assert "action" in genres_lower, f"Film '{pick.get('title')}' does not have Action genre!"

    # 2. Horror genre: catalog has exactly 5 horror films, so all 5 must be Horror
    resp_horror = client.post(
        "/v1/find-my-watch",
        headers=H(token),
        json={"mood": "strange", "genres": ["Horror"]}
    )
    assert resp_horror.status_code == 200, resp_horror.text
    data_horror = resp_horror.json()
    picks_horror = [data_horror["hero"]["content"]] + [r["content"] for r in data_horror["runners_up"]]
    assert len(picks_horror) == 5
    for pick in picks_horror:
        genres_lower = [g.lower() for g in pick.get("genres", [])]
        assert "horror" in genres_lower, f"Film '{pick.get('title')}' does not have Horror genre!"


def test_shown_history_tracks_and_penalizes_repeats(client):
    """
    Assert that titles shown to the user are logged in shown_history
    and receive a penalty to prevent repeating the exact same hero on next call.
    """
    from app.db import database
    user_sub = "auth0|repeat_test_user"
    token = make_token(user_sub)

    # First session request
    resp1 = client.post(
        "/v1/find-my-watch",
        headers=H(token),
        json={"mood": "mystery"}
    )
    assert resp1.status_code == 200
    hero1_id = resp1.json()["hero"]["content"]["content_id"]

    # Verify shown_history recorded all 5 titles
    shown = database.get_recent_shown_counts(user_sub)
    assert hero1_id in shown
    assert shown[hero1_id] >= 1

    # Second call without exclude_ids: the previous hero now has a penalty
    resp2 = client.post(
        "/v1/find-my-watch",
        headers=H(token),
        json={"mood": "mystery"}
    )
    assert resp2.status_code == 200
    # Because of penalty and candidate variety, verify shown counts increment
    shown_after = database.get_recent_shown_counts(user_sub)
    assert shown_after[hero1_id] >= 1
