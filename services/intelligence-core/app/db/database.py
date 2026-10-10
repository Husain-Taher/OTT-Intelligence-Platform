import sqlite3
import json
import os
from typing import Optional, List, Dict, Any, Tuple
from app.models.schemas import (
    CanonicalContent, ContentProfile, UserInteractionEvent, UserTasteVector,
    StoryCard, CastMemberDetail, UserProfile
)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "ott_intelligence.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Content table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS canonical_content (
        content_id TEXT PRIMARY KEY,
        tmdb_id INTEGER UNIQUE,
        title TEXT NOT NULL,
        original_title TEXT,
        content_type TEXT,
        release_date TEXT,
        release_year INTEGER,
        runtime INTEGER,
        genres TEXT, -- JSON list
        keywords TEXT, -- JSON list
        overview TEXT,
        tagline TEXT,
        original_language TEXT,
        origin_countries TEXT, -- JSON list
        directors TEXT, -- JSON list
        writers TEXT, -- JSON list
        cast_members TEXT, -- JSON list
        vote_average REAL,
        vote_count INTEGER,
        poster_path TEXT,
        backdrop_path TEXT,
        trailer_key TEXT,
        providers TEXT, -- JSON list
        profile TEXT, -- JSON dict of ContentProfile
        cast_detail TEXT, -- JSON list of CastMemberDetail
        gallery_images TEXT, -- JSON list of URLs
        story_card TEXT, -- JSON dict of StoryCard
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Migrations for existing DB
    for col in ["trailer_key", "cast_detail", "gallery_images", "story_card"]:
        try:
            cursor.execute(f"ALTER TABLE canonical_content ADD COLUMN {col} TEXT;")
        except Exception:
            pass

    # Users authentication & accounts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        avatar_url TEXT,
        archetype TEXT DEFAULT 'The Cerebral Philosopher',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # User taste vectors
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_taste_profiles (
        user_id TEXT PRIMARY KEY,
        genres TEXT,
        narrative TEXT,
        emotions TEXT,
        pacing TEXT,
        international TEXT,
        preferred_directors TEXT,
        abandoned_patterns TEXT,
        interaction_count INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # User Watchlist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_watchlist (
        user_id TEXT NOT NULL,
        content_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, content_id)
    );
    """)

    # Person profiles cache (photos, biography)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS person_profiles (
        name TEXT PRIMARY KEY,
        profile_path TEXT,
        known_for_department TEXT,
        biography TEXT
    );
    """)

    # Behavioral events stream
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        session_id TEXT,
        content_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        metadata TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Semantic embeddings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS content_embeddings (
        content_id TEXT PRIMARY KEY,
        embedding_vector TEXT,
        text_corpus TEXT
    );
    """)


    # Auth0-backed profiles (user_id = Auth0 `sub`)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        user_id TEXT PRIMARY KEY,
        display_name TEXT,
        email TEXT,
        picture TEXT,
        archetype TEXT,
        onboarded INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Every time the user sets the room's mood
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mood_checkins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        mood TEXT NOT NULL,
        genres TEXT,
        energy TEXT,
        max_runtime INTEGER,
        novelty REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mood_checkins_user ON mood_checkins(user_id, id DESC);")

    # What the user actually reaches for in each mood (accumulated signed signal per genre)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_mood_affinity (
        user_id TEXT NOT NULL,
        mood TEXT NOT NULL,
        genre TEXT NOT NULL,
        weight REAL DEFAULT 0,
        events INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, mood, genre)
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_user ON user_events(user_id, id DESC);")

    # One-tap feedback for UX study: Did this match your mood?
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pick_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        mood TEXT NOT NULL,
        content_id TEXT NOT NULL,
        matched INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pick_feedback_user ON pick_feedback(user_id, id DESC);")

    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

SELECT_COLUMNS = """
    content_id, tmdb_id, title, original_title, content_type,
    release_date, release_year, runtime, genres, keywords,
    overview, tagline, original_language, origin_countries,
    directors, writers, cast_members, vote_average, vote_count,
    poster_path, backdrop_path, trailer_key, providers, profile,
    cast_detail, gallery_images, story_card
"""

def save_content(item: CanonicalContent):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO canonical_content (
        content_id, tmdb_id, title, original_title, content_type,
        release_date, release_year, runtime, genres, keywords,
        overview, tagline, original_language, origin_countries,
        directors, writers, cast_members, vote_average, vote_count,
        poster_path, backdrop_path, trailer_key, providers, profile,
        cast_detail, gallery_images, story_card
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item.content_id,
        item.tmdb_id,
        item.title,
        item.original_title,
        item.content_type.value if hasattr(item.content_type, "value") else str(item.content_type),
        item.release_date,
        item.release_year,
        item.runtime,
        json.dumps(item.genres),
        json.dumps(item.keywords),
        item.overview,
        item.tagline,
        item.original_language,
        json.dumps(item.origin_countries),
        json.dumps(item.directors),
        json.dumps(item.writers),
        json.dumps(item.cast),
        item.vote_average,
        item.vote_count,
        item.poster_path,
        item.backdrop_path,
        item.trailer_key,
        json.dumps([p.model_dump() for p in item.providers]),
        json.dumps(item.profile.model_dump()) if item.profile else None,
        json.dumps([c.model_dump() for c in item.cast_detail]) if item.cast_detail else None,
        json.dumps(item.gallery_images) if item.gallery_images else None,
        json.dumps(item.story_card.model_dump()) if item.story_card else None
    ))
    conn.commit()
    conn.close()

def get_all_content() -> List[CanonicalContent]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT {SELECT_COLUMNS} FROM canonical_content ORDER BY vote_average DESC")
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        results.append(_row_to_content(row))
    return results

def get_content_by_id(content_id: str) -> Optional[CanonicalContent]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT {SELECT_COLUMNS} FROM canonical_content WHERE content_id = ?", (content_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_content(row)

def _row_to_content(row) -> CanonicalContent:
    trailer_key = row[21]
    providers_list = json.loads(row[22]) if row[22] else []
    profile_dict = json.loads(row[23]) if row[23] else None
    profile = ContentProfile(**profile_dict) if profile_dict else None
    cast_detail_list = [CastMemberDetail(**c) for c in json.loads(row[24])] if len(row) > 24 and row[24] else []
    gallery_list = json.loads(row[25]) if len(row) > 25 and row[25] else []
    story_card_dict = json.loads(row[26]) if len(row) > 26 and row[26] else None
    story_card = StoryCard(**story_card_dict) if story_card_dict else None

    # Fallback default story card if none generated yet
    if not story_card:
        story_card = StoryCard(
            thematic_pillars=[row[8].replace('[','').replace(']','').replace('"','').split(',')[0].strip() if row[8] else "Cinematic Journey", "Human Nature"],
            opening_hook=row[10][:130] + "..." if row[10] else "An intriguing opening premise pulls the viewer into high narrative stakes.",
            midpoint_escalation="Tension compounds as moral ambiguities force unexpected alliances.",
            climax_payoff="A powerful revelation culminating in high narrative and emotional payoff.",
            notable_dialogue=f"\"{row[11]}\"" if row[11] else None,
            visual_style_note="High atmospheric visual craft with distinctive lighting and cinematography."
        )

    # Fallback cast detail if empty
    if not cast_detail_list:
        cast_names = json.loads(row[16]) if row[16] else []
        cast_detail_list = [
            CastMemberDetail(name=n, character="Primary Cast", profile_path=None)
            for n in cast_names[:5]
        ]

    # Fallback gallery
    if not gallery_list:
        if row[20]: gallery_list.append(row[20])
        if row[19]: gallery_list.append(row[19])

    return CanonicalContent(
        content_id=row[0],
        tmdb_id=row[1],
        title=row[2],
        original_title=row[3],
        content_type=row[4],
        release_date=row[5],
        release_year=row[6],
        runtime=row[7],
        genres=json.loads(row[8]) if row[8] else [],
        keywords=json.loads(row[9]) if row[9] else [],
        overview=row[10] or "",
        tagline=row[11],
        original_language=row[12] or "en",
        origin_countries=json.loads(row[13]) if row[13] else [],
        directors=json.loads(row[14]) if row[14] else [],
        writers=json.loads(row[15]) if row[15] else [],
        cast=json.loads(row[16]) if row[16] else [],
        cast_detail=cast_detail_list,
        vote_average=row[17] or 0.0,
        vote_count=row[18] or 0,
        poster_path=row[19],
        backdrop_path=row[20],
        trailer_key=trailer_key,
        gallery_images=gallery_list,
        providers=providers_list,
        profile=profile,
        story_card=story_card
    )

def toggle_watchlist(user_id: str, content_id: str) -> bool:
    """Toggles item in user's saved watchlist. Returns True if now saved, False if removed."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM user_watchlist WHERE user_id = ? AND content_id = ?", (user_id, content_id))
    exists = cursor.fetchone()
    if exists:
        cursor.execute("DELETE FROM user_watchlist WHERE user_id = ? AND content_id = ?", (user_id, content_id))
        is_saved = False
    else:
        cursor.execute("INSERT INTO user_watchlist (user_id, content_id) VALUES (?, ?)", (user_id, content_id))
        is_saved = True
    conn.commit()
    conn.close()
    return is_saved

def get_watchlist(user_id: str) -> List[CanonicalContent]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT content_id FROM user_watchlist WHERE user_id = ? ORDER BY created_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for (cid,) in rows:
        item = get_content_by_id(cid)
        if item:
            results.append(item)
    return results

def is_in_watchlist(user_id: str, content_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM user_watchlist WHERE user_id = ? AND content_id = ?", (user_id, content_id))
    row = cursor.fetchone()
    conn.close()
    return bool(row)

def get_person_profile_photo(name: str) -> Optional[str]:
    """Retrieves profile photo URL for a director or star, caching to DB."""
    if not name or not name.strip():
        return None
    name = name.strip()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT profile_path FROM person_profiles WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row and row[0]:
        conn.close()
        return row[0]

    # Try lookup via TMDB API
    import urllib.request, urllib.parse
    key = os.getenv("TMDB_API_KEY", "9f28b17c76c356100ffb5d0257449d80")
    photo_url = None
    try:
        url = f"https://api.themoviedb.org/3/search/person?api_key={key}&query={urllib.parse.quote(name)}"
        req = urllib.request.Request(url, headers={"User-Agent": "OTT-Intelligence/1.0"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])
            if results and results[0].get("profile_path"):
                photo_url = f"https://image.tmdb.org/t/p/w300{results[0]['profile_path']}"
    except Exception:
        pass

    cursor.execute("""
    INSERT OR REPLACE INTO person_profiles (name, profile_path, known_for_department, biography)
    VALUES (?, ?, ?, ?)
    """, (name, photo_url, "Directing/Acting", ""))
    conn.commit()
    conn.close()
    return photo_url

def get_all_directors_and_stars() -> Dict[str, Any]:
    """Aggregates all directors and stars across the catalog with profile photos and titles ordered by rating."""
    all_content = get_all_content()
    directors_map: Dict[str, List[CanonicalContent]] = {}
    stars_map: Dict[str, List[CanonicalContent]] = {}

    for item in all_content:
        for d in item.directors:
            if d.strip():
                directors_map.setdefault(d.strip(), []).append(item)
        for s in item.cast[:5]:
            if s.strip():
                stars_map.setdefault(s.strip(), []).append(item)

    # Sort each person's titles by vote_average descending
    for d_name in directors_map:
        directors_map[d_name].sort(key=lambda x: x.vote_average, reverse=True)
    for s_name in stars_map:
        stars_map[s_name].sort(key=lambda x: x.vote_average, reverse=True)

    curated_directors = []
    for d_name, titles in sorted(directors_map.items(), key=lambda x: (len(x[1]), sum(t.vote_average for t in x[1])/len(x[1])), reverse=True):
        if len(titles) >= 1:
            photo = get_person_profile_photo(d_name)
            curated_directors.append({
                "name": d_name,
                "role": "Visionary Director",
                "profile_path": photo,
                "masterpiece_count": len(titles),
                "titles": titles,
                "avg_rating": round(sum(t.vote_average for t in titles) / len(titles), 1)
            })

    curated_stars = []
    for s_name, titles in sorted(stars_map.items(), key=lambda x: (len(x[1]), sum(t.vote_average for t in x[1])/len(x[1])), reverse=True):
        if len(titles) >= 1:
            photo = get_person_profile_photo(s_name)
            curated_stars.append({
                "name": s_name,
                "role": "Leading Star",
                "profile_path": photo,
                "starring_count": len(titles),
                "titles": titles,
                "avg_rating": round(sum(t.vote_average for t in titles) / len(titles), 1)
            })

    return {
        "directors": curated_directors,
        "stars": curated_stars
    }

def log_user_event(event: UserInteractionEvent):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO user_events (user_id, session_id, content_id, event_type, metadata)
    VALUES (?, ?, ?, ?, ?)
    """, (
        event.user_id,
        event.session_id,
        event.content_id,
        event.event_type,
        json.dumps(event.metadata)
    ))
    conn.commit()
    conn.close()

def get_user_events(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT user_id, session_id, content_id, event_type, metadata, created_at
    FROM user_events WHERE user_id = ? ORDER BY id DESC LIMIT ?
    """, (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [{
        "user_id": r[0],
        "session_id": r[1],
        "content_id": r[2],
        "event_type": r[3],
        "metadata": json.loads(r[4]) if r[4] else {},
        "created_at": r[5]
    } for r in rows]

def get_user_taste(user_id: str) -> Optional[UserTasteVector]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_taste_profiles WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return UserTasteVector(
        user_id=row[0],
        genres=json.loads(row[1]) if row[1] else {},
        narrative=json.loads(row[2]) if row[2] else {},
        emotions=json.loads(row[3]) if row[3] else {},
        pacing=json.loads(row[4]) if row[4] else {},
        international=json.loads(row[5]) if row[5] else {},
        preferred_directors=json.loads(row[6]) if row[6] else {},
        abandoned_patterns=json.loads(row[7]) if row[7] else {},
        interaction_count=row[8] or 0
    )

def save_user_taste(taste: UserTasteVector):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO user_taste_profiles (
        user_id, genres, narrative, emotions, pacing, international,
        preferred_directors, abandoned_patterns, interaction_count
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        taste.user_id,
        json.dumps(taste.genres),
        json.dumps(taste.narrative),
        json.dumps(taste.emotions),
        json.dumps(taste.pacing),
        json.dumps(taste.international),
        json.dumps(taste.preferred_directors),
        json.dumps(taste.abandoned_patterns),
        taste.interaction_count
    ))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Profiles, mood check-ins and mood-conditioned taste
# ---------------------------------------------------------------------------
import math

def ensure_profile(user_id: str, name: Optional[str] = None, email: Optional[str] = None, picture: Optional[str] = None):
    conn = get_connection()
    conn.execute("""
    INSERT INTO profiles (user_id, display_name, email, picture)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
        display_name = COALESCE(excluded.display_name, profiles.display_name),
        email = COALESCE(excluded.email, profiles.email),
        picture = COALESCE(excluded.picture, profiles.picture),
        last_seen = CURRENT_TIMESTAMP
    """, (user_id, name, email, picture))
    conn.commit()
    conn.close()

def get_profile_row(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute(
        "SELECT user_id, display_name, email, picture, archetype, onboarded, created_at FROM profiles WHERE user_id = ?",
        (user_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return {"user_id": row[0], "display_name": row[1], "email": row[2], "picture": row[3],
            "archetype": row[4], "onboarded": bool(row[5]), "created_at": row[6]}

def update_profile(user_id: str, archetype: Optional[str] = None, onboarded: Optional[bool] = None):
    conn = get_connection()
    if archetype is not None:
        conn.execute("UPDATE profiles SET archetype = ? WHERE user_id = ?", (archetype, user_id))
    if onboarded is not None:
        conn.execute("UPDATE profiles SET onboarded = ? WHERE user_id = ?", (1 if onboarded else 0, user_id))
    conn.commit()
    conn.close()

def log_mood_checkin(user_id: str, mood: str, genres: List[str], energy: Optional[str],
                     max_runtime: Optional[int], novelty: Optional[float]):
    conn = get_connection()
    conn.execute(
        "INSERT INTO mood_checkins (user_id, mood, genres, energy, max_runtime, novelty) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, mood, json.dumps(genres), energy, max_runtime, novelty))
    conn.commit()
    conn.close()

def get_recent_checkins(user_id: str, limit: int = 8) -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT mood, genres, energy, max_runtime, novelty, created_at FROM mood_checkins "
        "WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)).fetchall()
    conn.close()
    return [{"mood": r[0], "genres": json.loads(r[1]) if r[1] else [], "energy": r[2],
             "max_runtime": r[3], "novelty": r[4], "created_at": r[5]} for r in rows]

def get_checkin_counts(user_id: str) -> Dict[str, int]:
    conn = get_connection()
    rows = conn.execute("SELECT mood, COUNT(*) FROM mood_checkins WHERE user_id = ? GROUP BY mood", (user_id,)).fetchall()
    conn.close()
    return {m: c for m, c in rows}

def add_mood_affinity(user_id: str, mood: str, genres: List[str], signal: float):
    """Accumulates a signed signal for each genre of a title the user reacted to in `mood`."""
    if not genres or signal == 0:
        return
    conn = get_connection()
    for g in genres:
        conn.execute("""
        INSERT INTO user_mood_affinity (user_id, mood, genre, weight, events) VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(user_id, mood, genre) DO UPDATE SET weight = weight + excluded.weight, events = events + 1
        """, (user_id, mood, g, signal))
    conn.commit()
    conn.close()

def get_mood_affinity(user_id: str) -> Dict[str, Dict[str, Dict[str, float]]]:
    """{mood: {genre: {"weight": w, "events": n}}}"""
    conn = get_connection()
    rows = conn.execute("SELECT mood, genre, weight, events FROM user_mood_affinity WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    out: Dict[str, Dict[str, Dict[str, float]]] = {}
    for mood, genre, w, n in rows:
        out.setdefault(mood, {})[genre] = {"weight": w, "events": n}
    return out

def mood_genre_overlay(user_id: str, mood: str) -> Tuple[Dict[str, float], int]:
    """Genre scores (0..1) learned for this mood, and how many reactions back them."""
    per_genre = get_mood_affinity(user_id).get(mood, {})
    if not per_genre:
        return {}, 0
    overlay = {g: round(0.5 + 0.5 * math.tanh(v["weight"] / 3.0), 3) for g, v in per_genre.items()}
    reactions = int(max(v["events"] for v in per_genre.values()))
    return overlay, reactions

def get_user_activity_stats(user_id: str) -> Dict[str, Any]:
    """Real viewing stats derived from the event stream."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT DISTINCT e.content_id, c.runtime FROM user_events e
        JOIN canonical_content c ON c.content_id = e.content_id
        WHERE e.user_id = ? AND e.event_type IN ('WATCH_COMPLETE', 'REWATCH')
    """, (user_id,)).fetchall()
    likes = conn.execute("SELECT COUNT(DISTINCT content_id) FROM user_events WHERE user_id = ? AND event_type = 'LIKE'", (user_id,)).fetchone()[0]
    conn.close()
    minutes = sum(r[1] or 0 for r in rows)
    return {"titles_completed": len(rows), "hours_watched": round(minutes / 60.0, 1), "likes": likes}


def save_pick_feedback(user_id: str, mood: str, content_id: str, matched: int) -> int:
    """Store one-tap feedback from UX test participant."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pick_feedback (user_id, mood, content_id, matched)
        VALUES (?, ?, ?, ?)
    """, (user_id, mood, content_id, 1 if matched else 0))
    feedback_id = cur.lastrowid
    conn.commit()
    conn.close()
    return feedback_id


def get_all_pick_feedback() -> List[Dict[str, Any]]:
    """Retrieve all feedback entries for UX evaluation export."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT f.id, f.user_id, f.mood, f.content_id, c.title, f.matched, f.created_at
        FROM pick_feedback f
        LEFT JOIN canonical_content c ON c.content_id = f.content_id
        ORDER BY f.id ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

