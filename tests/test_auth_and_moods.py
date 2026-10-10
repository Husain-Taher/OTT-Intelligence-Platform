"""
Offline tests (no Auth0 tenant, no running server needed):
  pytest tests/test_auth_and_moods.py

A throwaway RSA key signs the tokens and the JWKS lookup is stubbed, so this exercises
the real verification code path: signature, issuer, audience, expiry, user isolation
and mood learning.
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


def make_token(sub="auth0|alice", aud=AUD, iss=ISS, exp_in=3600, key=_KEY):
    now = int(time.time())
    return jwt.encode({"sub": sub, "aud": aud, "iss": iss, "iat": now, "exp": now + exp_in}, key, algorithm="RS256")


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


def H(token):
    return {"Authorization": f"Bearer {token}"}


def test_requires_token(client):
    assert client.get("/v1/me").status_code == 401
    assert client.get("/v1/discover").status_code == 401
    assert client.get("/health").status_code == 200


@pytest.mark.parametrize("bad", [
    lambda: make_token(aud="https://someone-elses-api"),
    lambda: make_token(iss="https://evil.example.com/"),
    lambda: make_token(exp_in=-10),
    lambda: make_token(key=rsa.generate_private_key(public_exponent=65537, key_size=2048)),
])
def test_rejects_bad_tokens(client, bad):
    assert client.get("/v1/me", headers=H(bad())).status_code == 401


def test_identity_comes_from_token_not_client(client):
    alice, bob = H(make_token("auth0|alice")), H(make_token("auth0|bob"))
    me = client.get("/v1/me", headers={**alice, "x-user-name": "Alice"}).json()
    assert me["user_id"] == "auth0|alice" and me["display_name"] == "Alice"

    items = client.get("/v1/content", headers=alice).json()
    cid = items[0]["content_id"]
    # Spoofing another user's id in the body or query must not matter
    client.post("/v1/user/watchlist/toggle", headers=alice, json={"content_id": cid, "user_id": "auth0|bob"})
    assert client.get("/v1/user/watchlist", headers=alice).json()["count"] == 1
    assert client.get("/v1/user/watchlist?user_id=auth0|alice", headers=bob).json()["count"] == 0


def test_new_user_starts_uncalibrated(client):
    me = client.get("/v1/me", headers=H(make_token("auth0|newbie"))).json()
    assert me["calibration"] == 0 and me["onboarded"] is False
    assert all(m["reactions"] == 0 for m in me["mood_map"])


def test_mood_learning_changes_profile_and_recommendations(client):
    h = H(make_token("auth0|mia"))
    items = client.get("/v1/content", headers=h).json()
    animated = [i for i in items if "Animation" in i["genres"]][:4]
    assert len(animated) >= 3
    for it in animated:
        r = client.post("/v1/events", headers=h, json={"user_id": "x", "content_id": it["content_id"],
                                                        "event_type": "LIKE", "metadata": {"mood": "wholesome"}})
        assert r.json()["mood"] == "comforting"     # alias normalised
    me = client.get("/v1/me", headers=h).json()
    comfort = next(m for m in me["mood_map"] if m["mood"] == "comforting")
    assert comfort["learned"] and "Animation" in comfort["top_genres"]

    r = client.post("/v1/find-my-watch", headers=h, json={"mood": "comforting", "max_runtime": 150, "genres": ["Animation"]})
    assert r.status_code == 200 and r.json()["hero"]["content"]["title"]
    assert client.get("/v1/me", headers=h).json()["recent_checkins"][0]["mood"] == "comforting"


def test_every_mood_returns_a_pick(client):
    h = H(make_token("auth0|tester"))
    for mood in ["comforting", "emotional", "reflective", "mystery", "exciting", "romance", "strange"]:
        r = client.post("/v1/find-my-watch", headers=h, json={"mood": mood, "max_runtime": 180})
        assert r.status_code == 200, mood
        assert client.get(f"/v1/discover?mood={mood}", headers=h).json()["mood"] == mood


def test_saving_in_a_mood_teaches_that_mood(client):
    h = H(make_token("auth0|sam"))
    items = client.get("/v1/content", headers=h).json()
    horror = [i for i in items if "Mystery" in i["genres"]][:4]
    for it in horror:
        r = client.post("/v1/user/watchlist/toggle", headers=h, json={"content_id": it["content_id"], "mood": "mystery"})
        assert r.json()["is_saved"] is True
    mm = next(m for m in client.get("/v1/me", headers=h).json()["mood_map"] if m["mood"] == "mystery")
    assert mm["learned"] and "Mystery" in mm["top_genres"]
    # un-saving does not count as a positive signal
    client.post("/v1/user/watchlist/toggle", headers=h, json={"content_id": horror[0]["content_id"], "mood": "mystery"})
    assert client.get("/v1/user/watchlist", headers=h).json()["count"] == 3
