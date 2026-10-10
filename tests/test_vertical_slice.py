import urllib.request
import json

BASE = "http://127.0.0.1:8000/v1"

def test_vertical_slice():
    print("=== STARTING OTT INTELLIGENCE SYSTEM INTEGRATION TEST ===")
    
    # 1. Discovery Deck
    req = urllib.request.urlopen(f"{BASE}/discover")
    deck = json.loads(req.read().decode())
    assert deck["hero"] is not None, "Hero recommendation missing"
    assert len(deck["tonight_picks"]) > 0, "Tonight picks missing"
    print(f" PASS: Discovery deck verified. Hero: '{deck['hero']['content']['title']}' ({deck['hero']['personal_match_percentage']}% match)")

    # 2. Find My Watch Signature Decision Engine
    fmw_payload = json.dumps({
        "prompt": "I have 2 hours. I want something emotional but not depressing. A mystery with great visuals, preferably not American.",
        "mood": "mystery",
        "max_runtime": 130,
        "novelty": 0.7
    }).encode("utf-8")
    req = urllib.request.Request(f"{BASE}/find-my-watch", data=fmw_payload, headers={"Content-Type": "application/json"})
    fmw = json.loads(urllib.request.urlopen(req).read().decode())
    assert "hero" in fmw, "Find My Watch hero missing"
    assert "window_metrics" in fmw, "Window metrics missing"
    print(f" PASS: Find My Watch verified. Centerpiece: '{fmw['hero']['content']['title']}' ({fmw['hero']['personal_match_percentage']}%)")
    print(f"       Why this one: {fmw['hero']['contrasting_note']}")
    print(f"       Window Metrics: {fmw['window_metrics']}")

    # 3. Natural Language Search
    q = urllib.parse.quote("a Korean thriller with a satisfying ending")
    req = urllib.request.Request(f"{BASE}/search?query={q}", data=b"", headers={"Content-Type": "application/json"})
    search_res = json.loads(urllib.request.urlopen(req).read().decode())
    assert len(search_res["results"]) > 0, "Search results empty"
    print(f" PASS: Natural Search verified. Parsed intent: {search_res['parsed_intent']}")
    print(f"       Top match: '{search_res['results'][0]['content']['title']}' ({search_res['results'][0]['reasons']})")

    # 4. Taste Universe & Clusters
    req = urllib.request.urlopen(f"{BASE}/profile/taste-universe")
    universe = json.loads(req.read().decode())
    assert len(universe["clusters"]) >= 5, "Taste clusters missing"
    print(f" PASS: Taste Universe verified with {len(universe['clusters'])} cluster nodes.")

    # 5. Behavioral Event Logging & Live Preference Recalibration
    event_payload = json.dumps({
        "user_id": "default_user",
        "content_id": deck["hero"]["content"]["content_id"],
        "event_type": "WATCH_COMPLETE",
        "metadata": {"watch_duration_pct": 1.0}
    }).encode("utf-8")
    req = urllib.request.Request(f"{BASE}/events", data=event_payload, headers={"Content-Type": "application/json"})
    event_res = json.loads(urllib.request.urlopen(req).read().decode())
    assert event_res["status"] == "recorded"
    
    # Check updated taste vector
    req = urllib.request.urlopen(f"{BASE}/profile/taste")
    updated_taste = json.loads(req.read().decode())
    print(f" PASS: Behavioral event logged. User interaction count: {updated_taste['interaction_count']}")

    print("\nALL VERTICAL SLICE INTEGRATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_vertical_slice()
