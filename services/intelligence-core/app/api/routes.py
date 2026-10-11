import random
import math
import os
import csv
import io
import time
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Response
from typing import List, Optional, Dict, Any, Set
from app.models.schemas import (
    CanonicalContent, RecommendationIntent, RecommendationItem,
    UserTasteVector, UserInteractionEvent, UserProfile, FeedbackRequest
)
from app.db.database import (
    get_all_content, get_content_by_id, get_user_taste,
    save_user_taste, log_user_event, get_user_events,
    get_profile_row, update_profile, log_mood_checkin, get_recent_checkins,
    get_checkin_counts, add_mood_affinity, get_mood_affinity, mood_genre_overlay,
    get_user_activity_stats, get_watchlist, save_pick_feedback, get_all_pick_feedback,
    delete_user_data, log_shown_history, get_recent_shown_counts
)
from app.auth.auth0 import AuthUser, get_current_user
from app.moods import MOODS, normalize_mood, catalog as mood_catalog
from app.intelligence.taste_engine import TasteEngine, SIGNAL_WEIGHTS
from app.intelligence.semantic_engine import SemanticEngine
from app.recommender.candidate_generators import CandidateGenerator
from app.recommender.ranker import MultiStageRanker

# Every /v1 route needs a verified Auth0 token; the user id always comes from the token.
router = APIRouter(prefix="/v1", dependencies=[Depends(get_current_user)])

# Global singleton semantic engine
semantic_engine = SemanticEngine()

# In-memory cache for live world cinema fetching (1 hour TTL)
_WORLD_CINEMA_CACHE: Dict[str, Any] = {}

def get_initialized_semantic_engine() -> SemanticEngine:
    items = get_all_content()
    # Re-index if catalog size grew
    if not semantic_engine.is_fitted or len(semantic_engine.content_ids) != len(items):
        semantic_engine.build_index(items)
    return semantic_engine

def _load_taste(user_id: str) -> UserTasteVector:
    taste = get_user_taste(user_id)
    if not taste:
        # Real accounts start blank; only the local dev user keeps the demo persona.
        taste = (TasteEngine.get_default_taste(user_id) if user_id == "default_user"
                 else TasteEngine.get_blank_taste(user_id))
        save_user_taste(taste)
    return taste

MOOD_BLEND_MAX = 0.45      # how much a learned mood profile can pull genre taste
MOOD_BLEND_AFTER = 3       # reactions needed in a mood before it starts to count

def _taste_for_mood(user_id: str, mood: Optional[str]) -> UserTasteVector:
    """Global taste, nudged toward what this user actually reaches for in `mood` (never saved)."""
    taste = _load_taste(user_id)
    if not mood:
        return taste
    overlay, reactions = mood_genre_overlay(user_id, mood)
    if not overlay or reactions < MOOD_BLEND_AFTER:
        return taste
    strength = min(MOOD_BLEND_MAX, MOOD_BLEND_MAX * reactions / 10.0)
    blended = taste.model_copy(deep=True)
    for genre, learned in overlay.items():
        base = blended.genres.get(genre, 0.5)
        blended.genres[genre] = round((1 - strength) * base + strength * learned, 3)
    return blended

def _to_item(row) -> RecommendationItem:
    item, score, pct, breakdown, reasons, diffs, note = row
    return RecommendationItem(content=item, score=score, personal_match_percentage=pct,
                              match_breakdown=breakdown, reasons=reasons,
                              differences_from_usual=diffs, contrasting_note=note)

@router.get("/content", response_model=List[CanonicalContent])
def list_content():
    return get_all_content()

@router.get("/content/{content_id}", response_model=CanonicalContent)
def get_title(content_id: str):
    item = get_content_by_id(content_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content title not found")
    return item

@router.get("/content/{content_id}/insights")
def get_title_insights(content_id: str):
    item = get_content_by_id(content_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content title not found")
    return {
        "content_id": item.content_id,
        "title": item.title,
        "profile": item.profile,
        "providers": item.providers,
        "trailer_key": item.trailer_key
    }

@router.get("/content/{content_id}/similar")
def get_similar_titles(content_id: str, limit: int = 6):
    items = get_all_content()
    items_map = {i.content_id: i for i in items}
    engine = get_initialized_semantic_engine()
    results = engine.find_similar_to_title(content_id, items_map, top_k=limit)
    return [{"content": item, "similarity": sim} for item, sim in results]

def _ingest_event(user_id: str, content_id: str, event_type: str, metadata: Dict[str, Any], learn: bool = True) -> Optional[str]:
    """Logs a behavioural event and (optionally) teaches the global taste vector and the per-mood profile."""
    metadata = dict(metadata or {})
    mood = normalize_mood(metadata.get("mood"))
    if mood:
        metadata["mood"] = mood
    log_user_event(UserInteractionEvent(user_id=user_id, content_id=content_id,
                                        event_type=event_type, metadata=metadata))
    item = get_content_by_id(content_id) if learn else None
    if item:
        taste = _load_taste(user_id)
        save_user_taste(TasteEngine.update_taste_with_event(taste, item, event_type))
        # Mood-conditioned learning: remember what this user reaches for *in this mood*
        signal = SIGNAL_WEIGHTS.get(event_type, 0.0)
        if mood and abs(signal) >= 0.5:
            add_mood_affinity(user_id, mood, item.genres, signal)
    return mood

@router.post("/events")
def record_event(event: UserInteractionEvent, user: AuthUser = Depends(get_current_user)):
    # The user id always comes from the verified token, never from the request body.
    mood = _ingest_event(user.user_id, event.content_id, event.event_type, event.metadata or {})
    return {"status": "recorded", "event_type": event.event_type, "mood": mood}

@router.get("/profile/taste", response_model=UserTasteVector)
def get_taste_profile(user: AuthUser = Depends(get_current_user)):
    return _load_taste(user.user_id)

@router.post("/profile/archetype")
def select_archetype(archetype: str = Body(..., embed=True), user: AuthUser = Depends(get_current_user)):
    """
    Calibrates user taste vector based on a selected Cinephile Archetype.
    """
    user_id = user.user_id
    taste = _load_taste(user_id)
    if archetype == "cerebral":
        taste.genres = {"Science Fiction": 0.95, "Mystery": 0.90, "Drama": 0.75, "Thriller": 0.80}
        taste.narrative = {"mystery": 0.92, "complexity": 0.95, "philosophical": 0.95, "character_driven": 0.75}
        taste.emotions = {"WONDER": 0.95, "CURIOSITY": 0.92, "REFLECTION": 0.90, "SUSPENSE": 0.80}
        taste.pacing = {"slow_build": 0.85, "medium": 0.60, "fast": 0.20}
    elif archetype == "comfort":
        taste.genres = {"Comedy": 0.95, "Animation": 0.90, "Family": 0.85, "Drama": 0.70}
        taste.narrative = {"character_driven": 0.90, "complexity": 0.35, "mystery": 0.40, "philosophical": 0.50}
        taste.emotions = {"JOY": 0.95, "COMFORT": 0.95, "NOSTALGIA": 0.85, "HOPE": 0.90}
        taste.pacing = {"medium": 0.80, "slow_build": 0.50, "fast": 0.35}
    elif archetype == "adrenaline":
        taste.genres = {"Action": 0.98, "Thriller": 0.92, "Adventure": 0.85, "Crime": 0.80}
        taste.narrative = {"plot_driven": 0.95, "complexity": 0.45, "character_driven": 0.60}
        taste.emotions = {"TENSION": 0.95, "SUSPENSE": 0.90, "MOTIVATION": 0.85}
        taste.pacing = {"fast": 0.90, "medium": 0.70, "slow_build": 0.15}
    elif archetype == "emotional":
        taste.genres = {"Drama": 0.98, "Romance": 0.92, "History": 0.70}
        taste.narrative = {"character_driven": 0.98, "philosophical": 0.80, "complexity": 0.65}
        taste.emotions = {"SADNESS": 0.88, "REFLECTION": 0.95, "GRIEF": 0.75, "HOPE": 0.85, "ROMANCE": 0.90}
        taste.pacing = {"slow_build": 0.85, "medium": 0.65, "fast": 0.15}
    elif archetype == "international":
        taste.international = {"KR": 0.95, "JP": 0.92, "FR": 0.88, "DE": 0.85, "IN": 0.80, "US": 0.50}
        taste.genres = {"Thriller": 0.90, "Crime": 0.88, "Drama": 0.85}
        taste.narrative = {"mystery": 0.88, "complexity": 0.82}
    
    taste.interaction_count += 5
    save_user_taste(taste)
    update_profile(user_id, archetype=archetype)
    return {"status": "calibrated", "archetype": archetype, "taste": taste}

@router.post("/profile/tune-cluster")
def tune_cluster(
    cluster_id: str = Body(..., embed=True),
    weight: float = Body(..., embed=True),
    user: AuthUser = Depends(get_current_user)
):
    """
    Live slider tuning of a specific Taste Universe cluster node.
    """
    weight = max(0.0, min(1.0, weight))
    taste = _load_taste(user.user_id)
    if cluster_id == "c_scifi":
        taste.genres["Science Fiction"] = weight
        taste.emotions["WONDER"] = weight
    elif cluster_id == "c_mystery":
        taste.narrative["mystery"] = weight
        taste.genres["Mystery"] = weight
    elif cluster_id == "c_slowburn":
        taste.pacing["slow_build"] = weight
    elif cluster_id == "c_korean":
        taste.international["KR"] = weight
    elif cluster_id == "c_comfort":
        taste.emotions["COMFORT"] = weight
        taste.genres["Comedy"] = weight
    elif cluster_id == "c_adrenaline":
        taste.genres["Action"] = weight
        taste.emotions["TENSION"] = weight
    
    taste.interaction_count += 1
    save_user_taste(taste)
    return {"status": "tuned", "cluster_id": cluster_id, "weight": weight}

@router.get("/profile/taste-universe")
def get_taste_universe(user: AuthUser = Depends(get_current_user)):
    """
    Returns living 2D/3D cluster coordinates + orbiting titles for the user's Taste Universe (Section 33).
    """
    user_id = user.user_id
    all_items = get_all_content()
    taste = _load_taste(user_id)

    def find_orbit_titles(filter_fn, count=6):
        matched = [i for i in all_items if filter_fn(i)]
        scored = []
        for m in matched:
            pct, _, _, _ = TasteEngine.calculate_personal_match(taste, m)
            scored.append((m, pct))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [{"content": item, "personal_match_percentage": pct} for item, pct in scored[:count]]

    clusters = [
        {
            "id": "c_scifi",
            "name": "Sci-Fi & Cosmos",
            "tagline": "Existential world-building, mind-bending physics & wonder",
            "weight": taste.genres.get("Science Fiction", 0.85),
            "x": 120, "y": -90,
            "color": "#6366f1",
            "orbit_titles": find_orbit_titles(lambda i: "Science Fiction" in i.genres or (i.profile and i.profile.philosophical_depth > 0.7))
        },
        {
            "id": "c_mystery",
            "name": "Deep Mystery & Puzzles",
            "tagline": "Methodical investigation, psychological secrets & revelation",
            "weight": taste.narrative.get("mystery", 0.88),
            "x": -100, "y": -50,
            "color": "#8b5cf6",
            "orbit_titles": find_orbit_titles(lambda i: "Mystery" in i.genres or (i.profile and i.profile.mystery > 0.65))
        },
        {
            "id": "c_slowburn",
            "name": "Atmospheric Slow Burn",
            "tagline": "Unhurried narrative construction with high emotional payoff",
            "weight": taste.pacing.get("slow_build", 0.78),
            "x": -60, "y": 100,
            "color": "#ec4899",
            "orbit_titles": find_orbit_titles(lambda i: i.profile and i.profile.pacing.get("slow_build", 0) > 0.45)
        },
        {
            "id": "c_korean",
            "name": "Korean Thrillers & Auteurs",
            "tagline": "Visceral tension, moral ambiguity & sharp cinematic craft",
            "weight": taste.international.get("KR", 0.84),
            "x": 150, "y": 60,
            "color": "#14b8a6",
            "orbit_titles": find_orbit_titles(lambda i: "KR" in i.origin_countries)
        },
        {
            "id": "c_comfort",
            "name": "Comfort & Wholesome",
            "tagline": "Gentle charm, heartwarming joy & visual whimsy",
            "weight": taste.emotions.get("COMFORT", 0.70),
            "x": 0, "y": -150,
            "color": "#f59e0b",
            "orbit_titles": find_orbit_titles(lambda i: any(g in i.genres for g in ["Comedy", "Family", "Animation"]) or (i.profile and i.profile.emotions.get("COMFORT", 0) > 0.4))
        },
        {
            "id": "c_adrenaline",
            "name": "High Adrenaline & Kinetic",
            "tagline": "Unrelenting forward momentum, kinetic stuntcraft & pure spectacle",
            "weight": taste.genres.get("Action", 0.75),
            "x": 60, "y": 140,
            "color": "#ef4444",
            "orbit_titles": find_orbit_titles(lambda i: "Action" in i.genres or (i.profile and i.profile.emotions.get("TENSION", 0) > 0.65))
        }
    ]

    # Frontier Discovery (titles sitting outside the user's primary clusters with high novelty and masterpiece rating)
    primary_genres = {g for g, w in taste.genres.items() if w >= 0.7}
    frontier_candidates = [
        i for i in all_items 
        if i.vote_average >= 8.0 
        and not any(g in primary_genres for g in i.genres)
    ]
    if not frontier_candidates:
        frontier_candidates = [i for i in all_items if i.vote_average >= 8.2]
    
    frontier_scored = []
    for item in frontier_candidates:
        pct, breakdown, reasons, diffs = TasteEngine.calculate_personal_match(taste, item)
        frontier_scored.append({
            "content": item,
            "personal_match_percentage": pct,
            "novelty_score": 0.88,
            "discovery_reason": f"High-calibre {item.genres[0] if item.genres else 'cinema'} ({item.vote_average}★) outside your comfort zone"
        })
    frontier_scored.sort(key=lambda x: (x["content"].vote_average, -x["personal_match_percentage"]), reverse=True)

    return {
        "user_id": user_id,
        "interaction_count": taste.interaction_count,
        "clusters": clusters,
        "frontier_titles": frontier_scored[:8]
    }

@router.post("/profile/reset-taste")
def reset_user_taste_route(user: AuthUser = Depends(get_current_user)):
    """Resets user taste profile to neutral baseline."""
    taste = TasteEngine.get_blank_taste(user.user_id)
    save_user_taste(taste)
    return {"status": "reset", "user_id": user.user_id}

@router.post("/recommendations")
def get_recommendations(
    intent: RecommendationIntent = Body(...),
    limit: int = 10,
    user: AuthUser = Depends(get_current_user)
):
    all_items = get_all_content()
    engine = get_initialized_semantic_engine()
    intent.mood = normalize_mood(intent.mood) or intent.mood
    taste = _taste_for_mood(user.user_id, intent.mood)

    generator = CandidateGenerator(engine)
    candidates = generator.generate_candidates(all_items, taste, intent)
    ranked_tuples = MultiStageRanker.rank_and_diversify(candidates, taste, intent, top_n=limit)

    results: List[RecommendationItem] = []
    for item, final_score, match_pct, breakdown, reasons, diffs, contrast_note in ranked_tuples:
        results.append(RecommendationItem(
            content=item,
            score=final_score,
            personal_match_percentage=match_pct,
            match_breakdown=breakdown,
            reasons=reasons,
            differences_from_usual=diffs,
            contrasting_note=contrast_note
        ))

    return {"recommendations": results, "intent": intent}

@router.post("/find-my-watch")
def find_my_watch(
    prompt: Optional[str] = Body(None, embed=True),
    mood: Optional[str] = Body("mystery", embed=True),
    max_runtime: Optional[int] = Body(130, embed=True),
    novelty: float = Body(0.6, embed=True),
    exclude_ids: Optional[List[str]] = Body(None, embed=True),
    genres: Optional[List[str]] = Body(None, embed=True),
    energy: Optional[str] = Body(None, embed=True),
    year_min: Optional[int] = Body(None, embed=True),
    year_max: Optional[int] = Body(None, embed=True),
    min_rating: Optional[float] = Body(None, embed=True),
    language: Optional[str] = Body(None, embed=True),
    masterpiece_only: Optional[bool] = Body(False, embed=True),
    user: AuthUser = Depends(get_current_user)
):
    """
    Signature Experience (Section 80): Returns the centerpiece title + 4 runners-up
    strictly aligned with user's prompt, mood, and runtime limits.
    """
    user_id = user.user_id
    all_items = get_all_content()
    engine = get_initialized_semantic_engine()

    intent = engine.parse_natural_intent(prompt) if prompt else RecommendationIntent()
    canonical_mood = normalize_mood(mood)
    if canonical_mood:
        intent.mood = canonical_mood
    elif mood:
        intent.mood = mood
    if max_runtime:
        intent.max_runtime = max_runtime
    if genres:
        intent.target_genres = genres
    if energy:
        intent.energy = energy
    if year_min is not None:
        intent.year_min = year_min
    if year_max is not None:
        intent.year_max = year_max
    if min_rating is not None:
        intent.min_rating = min_rating
    if language is not None:
        intent.language = language
    if masterpiece_only:
        intent.masterpiece_only = masterpiece_only
    intent.novelty = max(0.0, min(1.0, novelty))
    taste = _taste_for_mood(user_id, canonical_mood or intent.mood)

    # A fresh show (not a "show me another") counts as a mood check-in for the profile
    if canonical_mood and not exclude_ids:
        log_mood_checkin(user_id, canonical_mood, genres or [], energy, max_runtime, intent.novelty)

    exclude_set = set(exclude_ids or [])
    shown_counts = get_recent_shown_counts(user_id, limit=50)

    generator = CandidateGenerator(engine)
    candidates = generator.generate_candidates(all_items, taste, intent, seen_content_ids=exclude_set)
    ranked = MultiStageRanker.rank_and_diversify(
        candidates, taste, intent, top_n=5, exclude_content_ids=exclude_set, shown_counts=shown_counts
    )

    if not ranked:
        # If hard constraints yielded no items when exclude_set was populated, allow repeating non-excluded items
        candidates = generator.generate_candidates(all_items, taste, intent, seen_content_ids=set())
        ranked = MultiStageRanker.rank_and_diversify(candidates, taste, intent, top_n=5, shown_counts=shown_counts)

    if not ranked:
        # If still empty due to strict query, gracefully return empty results rather than violating hard gates
        return {
            "hero": None,
            "runners_up": [],
            "intent": intent,
            "session_context": {"prompt": prompt, "mood": canonical_mood or intent.mood}
        }

    # Record shown history for newly presented titles
    presented_ids = [r[0].content_id for r in ranked]
    log_shown_history(user_id, presented_ids, mood=canonical_mood or intent.mood)

    hero_item, hero_score, hero_pct, hero_breakdown, hero_reasons, hero_diffs, hero_note = ranked[0]
    runners_up = []
    for item, score, pct, breakdown, reasons, diffs, note in ranked[1:]:
        runners_up.append(RecommendationItem(
            content=item,
            score=score,
            personal_match_percentage=pct,
            match_breakdown=breakdown,
            reasons=reasons,
            differences_from_usual=diffs,
            contrasting_note=note
        ))

    prof = hero_item.profile
    window_metrics = {
        "emotional_depth": int((prof.emotions.get("REFLECTION", 0.75) if prof else 0.75) * 100),
        "mystery_level": int((prof.mystery if prof else 0.8) * 100),
        "narrative_complexity": int((prof.narrative_complexity if prof else 0.7) * 100),
        "visual_atmosphere": prof.aspect_breakdown.atmosphere if prof else 92,
        "novelty_quotient": int(novelty * 100)
    }

    return {
        "hero": RecommendationItem(
            content=hero_item,
            score=hero_score,
            personal_match_percentage=hero_pct,
            match_breakdown=hero_breakdown,
            reasons=hero_reasons,
            differences_from_usual=hero_diffs,
            contrasting_note=hero_note
        ),
        "window_metrics": window_metrics,
        "runtime_formatted": f"{hero_item.runtime // 60}h {hero_item.runtime % 60}m" if hero_item.runtime else "2h 00m",
        "runners_up": runners_up
    }

@router.get("/discover")
def get_discovery_deck(
    hero_genre: Optional[str] = Query(None),
    mood: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user)
):
    """
    Discovery Home Deck (Section 29) with diverse thematic rails and dynamic hero.
    """
    user_id = user.user_id
    all_items = get_all_content()
    canonical_mood = normalize_mood(mood)
    taste = _taste_for_mood(user_id, canonical_mood)
    engine = get_initialized_semantic_engine()
    generator = CandidateGenerator(engine)

    # 1. Hero: best personal match among high-quality titles (not simply "first in the table")
    top_candidates = [i for i in all_items if i.vote_average >= 8.0]
    if hero_genre:
        top_candidates = [i for i in top_candidates if hero_genre.lower() in [g.lower() for g in i.genres]]

    if not top_candidates:
        top_candidates = all_items[:10]

    mood_picks: List[RecommendationItem] = []
    if canonical_mood:
        # Mood-aware deck: the whole lobby re-tunes to how the user feels right now
        m_intent = RecommendationIntent(mood=canonical_mood, novelty=0.5)
        cands = generator.generate_candidates(all_items, taste, m_intent)
        shown_counts = get_recent_shown_counts(user_id, limit=30)
        ranked_m = MultiStageRanker.rank_and_diversify(cands, taste, m_intent, top_n=7, shown_counts=shown_counts)
        mood_picks = [_to_item(r) for r in ranked_m]
        top_candidates = [mp.content for mp in mood_picks[:1]] or top_candidates

    chosen_hero_item = max(
        top_candidates[:40],
        key=lambda c: (TasteEngine.calculate_personal_match(taste, c)[0], c.vote_average)
    ) if top_candidates else all_items[0]
    h_pct, h_breakdown, h_reasons, h_diffs = TasteEngine.calculate_personal_match(taste, chosen_hero_item)
    hero_note = MultiStageRanker._generate_contrastive_note(chosen_hero_item, taste, RecommendationIntent(), h_pct)

    hero = RecommendationItem(
        content=chosen_hero_item,
        score=0.95,
        personal_match_percentage=h_pct,
        match_breakdown=h_breakdown,
        reasons=h_reasons,
        differences_from_usual=h_diffs,
        contrasting_note=hero_note
    )

    # 2. Curated Thematic Rails
    def filter_and_format(filter_fn, limit=6):
        items = [i for i in all_items if filter_fn(i) and i.content_id != hero.content.content_id][:limit]
        formatted = []
        for it in items:
            pct, bd, r, d = TasteEngine.calculate_personal_match(taste, it)
            formatted.append(RecommendationItem(
                content=it,
                score=0.9,
                personal_match_percentage=pct,
                match_breakdown=bd,
                reasons=r,
                differences_from_usual=d,
                contrasting_note=None
            ))
        return formatted

    # All-Time Acclaimed Greats: high vote count + top rated (e.g. Interstellar, Shawshank, Dark Knight, Godfather)
    # Bayesian popularity + rating ranker
    def bayes_rating(it):
        v = it.vote_count or 0
        r = it.vote_average or 0.0
        return (v / (v + 1000.0)) * r + (1000.0 / (v + 1000.0)) * 7.5

    greats_sorted = sorted([i for i in all_items if (i.vote_count or 0) >= 12000 and i.content_id != hero.content.content_id], key=bayes_rating, reverse=True)
    all_time_greats = []
    for it in greats_sorted[:8]:
        pct, bd, r, d = TasteEngine.calculate_personal_match(taste, it)
        all_time_greats.append(RecommendationItem(
            content=it,
            score=0.95,
            personal_match_percentage=pct,
            match_breakdown=bd,
            reasons=[f"Consensus Masterpiece ({it.vote_average}★, {it.vote_count:,} reviews)"],
            differences_from_usual=d,
            contrasting_note=None
        ))

    # Franchise Spotlight: spotlight beloved cinematic worlds (Harry Potter, LOTR, Dark Knight Trilogy)
    hp_titles = [i for i in all_items if "harry potter" in i.title.lower()]
    lotr_titles = [i for i in all_items if "lord of the rings" in i.title.lower()]
    batman_titles = [i for i in all_items if "dark knight" in i.title.lower() or "batman" in i.title.lower()]

    active_franchise_name = "The Wizarding World of Harry Potter"
    active_franchise_tagline = "Hogwarts, spells, friendship, and the battle against darkness"
    active_franchise_items = hp_titles if hp_titles else (lotr_titles or batman_titles)

    franchise_items_formatted = []
    for it in active_franchise_items[:6]:
        pct, bd, r, d = TasteEngine.calculate_personal_match(taste, it)
        franchise_items_formatted.append(RecommendationItem(
            content=it,
            score=0.92,
            personal_match_percentage=pct,
            match_breakdown=bd,
            reasons=[f"Iconic franchise chapter: {it.release_year}"],
            differences_from_usual=d,
            contrasting_note=None
        ))

    franchise_spotlight = {
        "franchise_name": active_franchise_name,
        "tagline": active_franchise_tagline,
        "titles": franchise_items_formatted
    }

    # Trending Now: high-energy contemporary cinematic spectacles
    trending_now = filter_and_format(
        lambda i: (i.release_year and i.release_year >= 2019 and (i.vote_count or 0) >= 3000),
        limit=6
    )

    tonight_picks = [mp for mp in mood_picks if mp.content.content_id != hero.content.content_id][:6] if mood_picks else filter_and_format(
        lambda i: "Science Fiction" in i.genres or "Mystery" in i.genres or "Drama" in i.genres,
        limit=6
    )

    unexpected_discoveries = filter_and_format(
        lambda i: any(c in ["KR", "JP", "FR", "DE", "IN", "IT", "BR"] for c in i.origin_countries),
        limit=6
    )

    comfort_rail = filter_and_format(
        lambda i: any(g in i.genres for g in ["Comedy", "Animation", "Family"]) or (i.profile and i.profile.emotions.get("COMFORT", 0) > 0.4),
        limit=6
    )

    adrenaline_rail = filter_and_format(
        lambda i: "Action" in i.genres or "Adventure" in i.genres or (i.profile and i.profile.emotions.get("TENSION", 0) > 0.6),
        limit=6
    )

    # 3. Dynamic Around the World Cinema (Live Open-Source Database Integration)
    # Fetches real-time, comprehensive collections of world cinema directly from TMDB
    def fetch_live_world_cinema(country_code=None, lang=None, genre_id=None, limit=12):
        cache_key = f"{country_code}:{lang}:{genre_id}:{limit}"
        now = time.time()
        if cache_key in _WORLD_CINEMA_CACHE:
            cached_time, cached_items = _WORLD_CINEMA_CACHE[cache_key]
            if now - cached_time < 3600:
                return cached_items

        key = os.getenv("TMDB_API_KEY", "9f28b17c76c356100ffb5d0257449d80")
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={key}&sort_by=vote_count.desc&page=1"
        if country_code:
            url += f"&with_origin_country={country_code}"
        if lang:
            url += f"&with_original_language={lang}"
        if genre_id:
            url += f"&with_genres={genre_id}"
        
        live_items = []
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OTT-Intelligence/1.0"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for m in data.get("results", [])[:limit]:
                    m_id = m.get("id")
                    m_title = m.get("title")
                    m_release = int(m.get("release_date")[:4]) if m.get("release_date") else None
                    m_poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get("poster_path") else None
                    m_backdrop = f"https://image.tmdb.org/t/p/original{m['backdrop_path']}" if m.get("backdrop_path") else None
                    
                    # Check if already cached in canonical database
                    existing = next((it for it in all_items if it.tmdb_id == m_id or it.title.lower() == m_title.lower()), None)
                    if existing:
                        live_items.append(existing)
                    else:
                        live_items.append(CanonicalContent(
                            content_id=f"online_movie_{m_id}",
                            tmdb_id=m_id,
                            title=m_title,
                            original_title=m.get("original_title"),
                            release_date=m.get("release_date"),
                            release_year=m_release,
                            overview=m.get("overview", ""),
                            original_language=m.get("original_language", "en"),
                            vote_average=round(float(m.get("vote_average", 0.0)), 1),
                            vote_count=int(m.get("vote_count", 0)),
                            poster_path=m_poster,
                            backdrop_path=m_backdrop
                        ))
                if live_items:
                    _WORLD_CINEMA_CACHE[cache_key] = (now, live_items)
        except Exception as e:
            # Fallback to local catalog if offline
            pass
        return live_items

    # Fetch live Indian Cinema / Bollywood (Hindi & Pan-India blockbusters)
    live_bollywood = fetch_live_world_cinema(lang="hi", limit=12)
    live_korean = fetch_live_world_cinema(country_code="KR", limit=12)
    live_japanese = fetch_live_world_cinema(country_code="JP", limit=12)
    live_european = fetch_live_world_cinema(country_code="FR", limit=12)

    # Fallback to local catalog if external network timed out
    around_the_world = {
        "India & Bollywood Masterpieces": live_bollywood or [i for i in all_items if "IN" in i.origin_countries or i.original_language in ["hi", "ta", "te"]][:12],
        "South Korean Cinema & Auteurs": live_korean or [i for i in all_items if "KR" in i.origin_countries][:12],
        "Japanese Masterpieces & Anime": live_japanese or [i for i in all_items if "JP" in i.origin_countries][:12],
        "European & French Cinema": live_european or [i for i in all_items if any(c in ["FR", "DE", "ES", "IT"] for c in i.origin_countries)][:12],
    }

    # Indian cinema rail populated with live + local database
    indian_items = live_bollywood or [i for i in all_items if "IN" in i.origin_countries or i.original_language in ["hi", "ta", "te", "kn", "ml"]]
    indian_cinema_rail = []
    for it in indian_items[:12]:
        pct, bd, r, d = TasteEngine.calculate_personal_match(taste, it)
        indian_cinema_rail.append(RecommendationItem(
            content=it,
            score=0.9,
            personal_match_percentage=pct,
            match_breakdown=bd,
            reasons=[f"Critically acclaimed Indian cinema ({it.release_year or 'Classic'})"],
            differences_from_usual=d,
            contrasting_note=None
        ))

    return {
        "mood": canonical_mood,
        "hero": hero,
        "tonight_picks": tonight_picks,
        "all_time_greats": all_time_greats,
        "franchise_spotlight": franchise_spotlight,
        "trending_now": trending_now,
        "unexpected_discoveries": unexpected_discoveries,
        "comfort_rail": comfort_rail,
        "adrenaline_rail": adrenaline_rail,
        "indian_cinema_rail": indian_cinema_rail,
        "around_the_world": around_the_world,
        "total_catalog_size": len(all_items)
    }

@router.post("/search")
def natural_search(query: str = Query(...), user: AuthUser = Depends(get_current_user)):
    """
    Hybrid Search: combines deep local semantic / taste index with live online open-source database (TMDB).
    Guarantees that ANY movie from across cinema history can be found instantly!
    """
    all_items = get_all_content()
    engine = get_initialized_semantic_engine()
    taste = _taste_for_mood(user.user_id, None)

    # 1. First, search local database using multi-stage ranker
    intent = engine.parse_natural_intent(query)
    taste = _taste_for_mood(user.user_id, normalize_mood(intent.mood))
    generator = CandidateGenerator(engine)
    candidates = generator.generate_candidates(all_items, taste, intent)
    ranked = MultiStageRanker.rank_and_diversify(candidates, taste, intent, top_n=12)

    local_results = [
        RecommendationItem(
            content=item,
            score=score,
            personal_match_percentage=pct,
            match_breakdown=breakdown,
            reasons=reasons,
            differences_from_usual=diffs,
            contrasting_note=note
        )
        for item, score, pct, breakdown, reasons, diffs, note in ranked
    ]

    # 2. Live Online Open-Source Database Search (TMDB)
    # If the user searched for ANY title outside our seeded catalog, fetch it live!
    online_results: List[RecommendationItem] = []
    seen_titles = {r.content.title.lower() for r in local_results}
    try:
        key = os.getenv("TMDB_API_KEY", "9f28b17c76c356100ffb5d0257449d80")
        url = f"https://api.themoviedb.org/3/search/movie?api_key={key}&query={urllib.parse.quote(query.strip())}"
        req = urllib.request.Request(url, headers={"User-Agent": "OTT-Intelligence/1.0"})
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for m in data.get("results", [])[:10]:
                title = m.get("title", "")
                if not title or title.lower() in seen_titles:
                    continue
                seen_titles.add(title.lower())
                m_id = m.get("id")
                m_release = int(m.get("release_date")[:4]) if m.get("release_date") else None
                m_poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get("poster_path") else None
                m_backdrop = f"https://image.tmdb.org/t/p/original{m['backdrop_path']}" if m.get("backdrop_path") else None
                
                online_item = CanonicalContent(
                    content_id=f"online_movie_{m_id}",
                    tmdb_id=m_id,
                    title=title,
                    original_title=m.get("original_title"),
                    release_date=m.get("release_date"),
                    release_year=m_release,
                    overview=m.get("overview", ""),
                    original_language=m.get("original_language", "en"),
                    vote_average=round(float(m.get("vote_average", 0.0)), 1),
                    vote_count=int(m.get("vote_count", 0)),
                    poster_path=m_poster,
                    backdrop_path=m_backdrop
                )
                pct, bd, r, d = TasteEngine.calculate_personal_match(taste, online_item)
                online_results.append(RecommendationItem(
                    content=online_item,
                    score=0.88,
                    personal_match_percentage=pct,
                    match_breakdown=bd,
                    reasons=[f"Discovered via Global Cinema Database ({m_release or 'Classic'}, {online_item.vote_average}★)"],
                    differences_from_usual=d,
                    contrasting_note=None
                ))
    except Exception as e:
        pass

    # Blend: Prioritize exact matches from local and online
    combined_results = local_results + online_results

    # If the online query was an exact title match (e.g. "Sholay", "Dilwale Dulhania Le Jayenge"), surface it first!
    q_low = query.strip().lower()
    combined_results.sort(key=lambda r: (r.content.title.lower() == q_low, r.score), reverse=True)

    return {
        "query": query,
        "parsed_intent": intent,
        "results": combined_results[:18]
    }

@router.get("/people")
def get_people_hub():
    """Returns visionary directors and leading stars with their filmographies."""
    from app.db.database import get_all_directors_and_stars
    return get_all_directors_and_stars()

@router.get("/people/search")
def search_person_online(query: str = Query(...)):
    """Live search for ANY actor, director, or creator online via TMDB and local engine.
    Returns their profile, biography, photo, and complete filmography ordered by viewer rating.
    """
    import os, urllib.request, urllib.parse, json
    from app.db.database import get_all_content, get_person_profile_photo
    query = query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Search query is required")

    key = os.getenv("TMDB_API_KEY", "9f28b17c76c356100ffb5d0257449d80")
    local_catalog = get_all_content()
    local_map = {item.title.lower(): item for item in local_catalog}

    results = []
    try:
        url = f"https://api.themoviedb.org/3/search/person?api_key={key}&query={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "OTT-Intelligence/1.0"})
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            people_hits = data.get("results", [])

            for p in people_hits[:8]:
                person_id = p.get("id")
                name = p.get("name")
                known_for_dept = p.get("known_for_department", "Acting")
                role = "Visionary Director" if known_for_dept == "Directing" else "Leading Star"
                profile_path = f"https://image.tmdb.org/t/p/w300{p['profile_path']}" if p.get("profile_path") else None
                popularity = p.get("popularity", 0.0)

                # Fetch full movie credits
                credits_url = f"https://api.themoviedb.org/3/person/{person_id}/movie_credits?api_key={key}"
                req_credits = urllib.request.Request(credits_url, headers={"User-Agent": "OTT-Intelligence/1.0"})
                with urllib.request.urlopen(req_credits, timeout=5.0) as c_resp:
                    c_data = json.loads(c_resp.read().decode("utf-8"))

                # Choose credits based on department
                raw_movies = c_data.get("crew", []) if known_for_dept == "Directing" else c_data.get("cast", [])
                if known_for_dept == "Directing":
                    raw_movies = [m for m in raw_movies if m.get("job") == "Director"]
                if not raw_movies:
                    # fallback to whatever is available
                    raw_movies = c_data.get("cast", []) or c_data.get("crew", [])

                # Filter valid titles with minimum vote threshold
                valid_movies = [m for m in raw_movies if m.get("title") and m.get("vote_count", 0) >= 15]
                # Sort by rating descending
                valid_movies.sort(key=lambda x: (x.get("vote_average", 0), x.get("vote_count", 0)), reverse=True)

                filmography = []
                for m in valid_movies[:20]:
                    m_title = m.get("title")
                    m_release = m.get("release_date", "")[:4] if m.get("release_date") else None
                    m_rating = round(m.get("vote_average", 0.0), 1)
                    m_votes = m.get("vote_count", 0)
                    m_poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get("poster_path") else None
                    m_backdrop = f"https://image.tmdb.org/t/p/original{m['backdrop_path']}" if m.get("backdrop_path") else None
                    m_overview = m.get("overview", "")
                    
                    # Check if already in our local deep canonical database
                    existing = local_map.get(m_title.lower())
                    content_id = existing.content_id if existing else f"online_movie_{m.get('id')}"
                    trailer_key = existing.trailer_key if existing else None
                    genres = existing.genres if existing else []

                    filmography.append({
                        "content_id": content_id,
                        "title": m_title,
                        "release_year": int(m_release) if m_release and m_release.isdigit() else None,
                        "vote_average": m_rating,
                        "vote_count": m_votes,
                        "poster_path": m_poster,
                        "backdrop_path": m_backdrop,
                        "overview": m_overview,
                        "character": m.get("character") or ("Director" if known_for_dept == "Directing" else "Leading Role"),
                        "genres": genres,
                        "trailer_key": trailer_key,
                        "in_local_catalog": bool(existing)
                    })

                avg_rating = round(sum(m["vote_average"] for m in filmography) / max(len(filmography), 1), 1)

                results.append({
                    "person_id": person_id,
                    "name": name,
                    "role": role,
                    "known_for_department": known_for_dept,
                    "profile_path": profile_path,
                    "popularity": popularity,
                    "avg_rating": avg_rating,
                    "filmography_count": len(filmography),
                    "titles": filmography
                })

    except Exception as e:
        print("Person search online error:", e)

    return {
        "query": query,
        "count": len(results),
        "results": results
    }

@router.get("/people/character-vibe")
def match_character_vibe(
    actor_name: str = Query(...),
    character_name: Optional[str] = Query(None),
    reference_title: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user)
):
    """
    Finds titles and characters with the same psychological/narrative vibe as an actor's character.
    e.g. Cillian Murphy as J. Robert Oppenheimer / Thomas Shelby -> complex, intense, slow-burn psychological dramas.
    """
    all_items = get_all_content()
    engine = get_initialized_semantic_engine()
    taste = _load_taste(user.user_id)

    # 1. Synthesize character query representation
    query_parts = [actor_name]
    if character_name:
        query_parts.append(f"as {character_name}")
    if reference_title:
        query_parts.append(f"in {reference_title}")
    
    char_query = " ".join(query_parts)
    
    # 2. Extract semantic intent & vector
    parsed_intent = engine.parse_natural_intent(f"character study like {char_query} intense complex deep performance")
    
    # Check if we have the reference title to derive its emotion/pacing profile
    ref_item = None
    if reference_title:
        ref_item = next((i for i in all_items if reference_title.lower() in i.title.lower()), None)
    
    candidates = []
    for item in all_items:
        # Exclude the exact reference title
        if ref_item and item.content_id == ref_item.content_id:
            continue
        
        # Calculate mood/vibe match
        match_score = 0.0
        reasons = []
        
        # Actor appearance boost
        has_same_actor = actor_name.lower() in [c.lower() for c in item.cast]
        if has_same_actor:
            match_score += 0.35
            reasons.append(f"Features {actor_name} delivering a signature performance")
        
        # Character/thematic vector similarity
        if engine.vector_index:
            sim = engine.vector_index.search(char_query, top_k=50)
            sim_dict = {cid: s for cid, s in sim}
            if item.content_id in sim_dict:
                match_score += sim_dict[item.content_id] * 0.40

        # Profile emotion & intensity alignment
        if ref_item and ref_item.profile and item.profile:
            ref_emotions = set(k for k, v in ref_item.profile.emotions.items() if v >= 0.4)
            item_emotions = set(k for k, v in item.profile.emotions.items() if v >= 0.4)
            common_emotions = ref_emotions.intersection(item_emotions)
            if common_emotions:
                match_score += len(common_emotions) * 0.1
                reasons.append(f"Shares emotional tone: {', '.join(list(common_emotions)[:2]).title()}")
            
            # Pacing alignment
            dominant_ref_pace = max(ref_item.profile.pacing.items(), key=lambda x: x[1])[0]
            if item.profile.pacing.get(dominant_ref_pace, 0) > 0.5:
                match_score += 0.15
                reasons.append(f"Matching {dominant_ref_pace.replace('_', ' ')} narrative progression")

        if match_score > 0.3 or has_same_actor:
            pct = int(min(98, max(50, match_score * 100)))
            if not reasons:
                reasons.append(f"Resonates with the complex character energy of {char_query}")
            
            candidates.append({
                "content": item,
                "character_vibe_score": round(match_score, 3),
                "personal_match_percentage": pct,
                "vibe_reasons": reasons[:3],
                "matched_character_archetype": f"Complex performance akin to {character_name or actor_name}"
            })

    candidates.sort(key=lambda x: (x["character_vibe_score"], x["content"].vote_average), reverse=True)

    return {
        "actor_name": actor_name,
        "character_name": character_name,
        "reference_title": reference_title,
        "archetype_summary": f"Characters and films channeling the intense, magnetic aura of {char_query}",
        "count": len(candidates),
        "results": candidates[:12]
    }

@router.get("/user/watchlist")
def get_user_watchlist_route(user: AuthUser = Depends(get_current_user)):
    """Returns user's saved watchlist."""
    items = get_watchlist(user.user_id)
    return {"user_id": user.user_id, "count": len(items), "items": items}

@router.post("/user/watchlist/toggle")
def toggle_user_watchlist_route(
    content_id: str = Body(..., embed=True),
    mood: Optional[str] = Body(None, embed=True),
    user: AuthUser = Depends(get_current_user)
):
    """Adds or removes a title from personal watchlist."""
    from app.db.database import toggle_watchlist
    user_id = user.user_id
    is_saved = toggle_watchlist(user_id, content_id)
    # Saving teaches the profile (in the current mood); un-saving is only logged.
    _ingest_event(user_id, content_id, "SAVE" if is_saved else "REMOVE_SAVE",
                  {"mood": mood} if mood else {}, learn=is_saved)
    return {"status": "success", "content_id": content_id, "is_saved": is_saved}

# --- MOODS, PROFILE & IDENTITY ---
@router.get("/moods")
def list_moods():
    """Mood catalog with genre hints limited to genres that exist in the catalog."""
    genres = sorted({g for i in get_all_content() for g in i.genres})
    return {"moods": mood_catalog(genres), "genres": genres}

@router.get("/me")
def get_me(user: AuthUser = Depends(get_current_user)):
    """The signed-in user's profile card: identity, real viewing stats, taste and mood map."""
    user_id = user.user_id
    row = get_profile_row(user_id) or {}
    taste = _load_taste(user_id)
    stats = get_user_activity_stats(user_id)
    watchlist = get_watchlist(user_id)

    top_genres = [{"name": k, "weight": int(v * 100)}
                  for k, v in sorted(taste.genres.items(), key=lambda x: x[1], reverse=True)[:5]]
    top_directors = [k for k, _ in sorted(taste.preferred_directors.items(), key=lambda x: x[1], reverse=True)[:4]]
    # How well the system knows this user: 0 on day one, ~90 after ~35 reactions
    calibration = int(round(100 * (1 - math.exp(-taste.interaction_count / 15.0))))

    affinity = get_mood_affinity(user_id)
    checkins = get_checkin_counts(user_id)
    mood_map = []
    for mood_id in MOODS:
        genres = affinity.get(mood_id, {})
        ranked = sorted(((g, v["weight"]) for g, v in genres.items() if v["weight"] > 0), key=lambda x: -x[1])[:3]
        reactions = int(max((v["events"] for v in genres.values()), default=0))
        mood_map.append({
            "mood": mood_id,
            "checkins": checkins.get(mood_id, 0),
            "reactions": reactions,
            "top_genres": [g for g, _ in ranked],
            "learned": reactions >= MOOD_BLEND_AFTER and bool(ranked),
        })

    return {
        "user_id": user_id,
        "display_name": row.get("display_name") or user.name or "Guest",
        "email": row.get("email") or user.email,
        "picture": row.get("picture") or user.picture,
        "archetype": row.get("archetype"),
        "onboarded": bool(row.get("onboarded")),
        "member_since": row.get("created_at"),
        "stats": {**stats, "saved": len(watchlist), "reactions": taste.interaction_count},
        "calibration": calibration,
        "top_genres": top_genres,
        "top_directors": top_directors,
        "mood_map": mood_map,
        "recent_checkins": get_recent_checkins(user_id, 8),
    }

@router.post("/me/onboarded")
def finish_onboarding(user: AuthUser = Depends(get_current_user)):
    update_profile(user.user_id, onboarded=True)
    return {"status": "ok"}

@router.delete("/me")
def delete_me(user: AuthUser = Depends(get_current_user)):
    """Removes the authenticated user's profile, events, mood map, and watchlist."""
    delete_user_data(user.user_id)
    return {"status": "deleted"}


# --- MASTER ML TRAINING PIPELINE ROUTES ---
@router.post("/ml/train-user")
def trigger_ml_training_route(user: AuthUser = Depends(get_current_user)):
    """
    Executes the self-learning ML pipeline:
    Synthesizes historical behavioral events, applies time-decay weights,
    re-calibrates 20-dimensional taste vectors, and updates cluster coordinates.
    """
    from app.intelligence.ml_pipeline import MLTrainingPipeline
    result = MLTrainingPipeline.train_user_taste(user.user_id)
    return {"status": "success", "ml_training_result": result}

@router.get("/ml/health")
def get_ml_health_route():
    """Returns status of model training engines, feature stores, and data pipelines."""
    all_content = get_all_content()
    engine = get_initialized_semantic_engine()
    return {
        "status": "operational",
        "model_version": "v3.4-continuous-online",
        "catalog_vectors": len(all_content),
        "semantic_engine_fitted": engine.is_fitted,
        "features": [
            "Exponential Time-Decay Weighting",
            "Multi-Signal Event Digestion (WATCH, ABANDON, TRAILER, SAVE)",
            "Dynamic Archetype Clustering",
            "Zero-Cost Open-Source SQLite Persistence"
        ]
    }

@router.post("/feedback")
def submit_pick_feedback(
    feedback: FeedbackRequest,
    user: AuthUser = Depends(get_current_user)
):
    """Store one-tap feedback from UX test participant under Mood Studio pick."""
    fid = save_pick_feedback(
        user_id=user.user_id,
        mood=feedback.mood,
        content_id=feedback.content_id,
        matched=feedback.matched
    )
    return {"status": "success", "id": fid}

@router.get("/admin/export.csv")
def export_feedback_csv(
    user: AuthUser = Depends(get_current_user)
):
    """Export the UX study feedback table as CSV, restricted to ADMIN_SUB."""
    admin_sub = os.getenv("ADMIN_SUB", "").strip()
    # In local dev / test environments or when matching ADMIN_SUB, allow export
    if admin_sub and user.user_id != admin_sub and user.user_id != "default_user":
        raise HTTPException(status_code=403, detail="Forbidden: admin access required")

    entries = get_all_pick_feedback()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "user_id", "mood", "content_id", "title", "matched", "created_at"])
    for e in entries:
        writer.writerow([
            e.get("id"),
            e.get("user_id"),
            e.get("mood"),
            e.get("content_id"),
            e.get("title") or "",
            e.get("matched"),
            e.get("created_at")
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="pick_feedback_export.csv"'}
    )


@router.post("/admin/refresh-similarity")
def refresh_similarity_job(
    user: AuthUser = Depends(get_current_user)
):
    """
    Nightly/Periodic maintenance job (Phase 7):
    Re-indexes catalog dense vector embeddings and refreshes content-to-content similarity index.
    """
    admin_sub = os.getenv("ADMIN_SUB", "").strip()
    if admin_sub and user.user_id != admin_sub and user.user_id != "default_user":
        raise HTTPException(status_code=403, detail="Forbidden: admin access required")

    items = get_all_content()
    engine = get_initialized_semantic_engine()
    engine.build_index(items)

    from app.intelligence.tagger import ContentTagger
    from app.db.database import save_mood_scores
    for it in items:
        tag_res = ContentTagger.tag_content(it)
        save_mood_scores(it.content_id, tag_res.mood_scores, tag_res.primary_cues)

    return {
        "status": "refreshed",
        "indexed_items": len(items),
        "timestamp": time.time()
    }


