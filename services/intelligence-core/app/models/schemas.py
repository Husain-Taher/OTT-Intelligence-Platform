from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum

class ContentType(str, Enum):
    MOVIE = "movie"
    SERIES = "series"

class PacingCategory(str, Enum):
    SLOW_BUILD = "slow_build"
    MEDIUM = "medium"
    FAST = "fast"

class EmotionType(str, Enum):
    AWE = "AWE"
    WONDER = "WONDER"
    JOY = "JOY"
    COMFORT = "COMFORT"
    NOSTALGIA = "NOSTALGIA"
    TENSION = "TENSION"
    SUSPENSE = "SUSPENSE"
    FEAR = "FEAR"
    ANXIETY = "ANXIETY"
    SADNESS = "SADNESS"
    GRIEF = "GRIEF"
    HOPE = "HOPE"
    INSPIRATION = "INSPIRATION"
    ROMANCE = "ROMANCE"
    CURIOSITY = "CURIOSITY"
    CONFUSION = "CONFUSION"
    FRUSTRATION = "FRUSTRATION"
    SATISFACTION = "SATISFACTION"
    REFLECTION = "REFLECTION"
    MOTIVATION = "MOTIVATION"

class StreamingProvider(BaseModel):
    provider_id: int
    provider_name: str
    logo_path: Optional[str] = None
    type: str = "flatrate"  # flatrate, rent, buy

class ReviewQuote(BaseModel):
    id: str
    text: str
    aspect: str  # "cinematography", "pacing", "acting", "emotional_impact", etc.
    sentiment: str  # "positive", "negative", "mixed"
    tag: str  # "EMOTIONAL IMPACT", "PACING WARNING", "VISUAL ATMOSPHERE"
    source: str = "TMDB Viewer Review"
    author: Optional[str] = "Verified Reviewer"
    confidence: float = 0.9

class AspectBreakdown(BaseModel):
    atmosphere: int = 85
    characters: int = 80
    story: int = 82
    acting: int = 88
    music: int = 84
    pacing_rating: int = 68
    ending_satisfaction: int = 78

class CastMemberDetail(BaseModel):
    name: str
    character: Optional[str] = None
    profile_path: Optional[str] = None

class StoryCard(BaseModel):
    thematic_pillars: List[str] = Field(default_factory=list)
    opening_hook: str = ""
    midpoint_escalation: str = ""
    climax_payoff: str = ""
    notable_dialogue: Optional[str] = None
    visual_style_note: Optional[str] = None

class ContentProfile(BaseModel):
    narrative_complexity: float = Field(0.5, ge=0.0, le=1.0)
    mystery: float = Field(0.5, ge=0.0, le=1.0)
    philosophical_depth: float = Field(0.5, ge=0.0, le=1.0)
    character_driven: float = Field(0.5, ge=0.0, le=1.0)
    plot_driven: float = Field(0.5, ge=0.0, le=1.0)
    pacing: Dict[str, float] = Field(default_factory=lambda: {"slow_build": 0.4, "medium": 0.5, "fast": 0.1})
    emotions: Dict[str, float] = Field(default_factory=dict)  # map EmotionType -> score (0.0 to 1.0)
    audience_reaction: Dict[str, int] = Field(default_factory=dict) # Suspense: 88, Emotion: 75, etc.
    aspect_breakdown: AspectBreakdown = Field(default_factory=AspectBreakdown)
    highlighted_quotes: List[ReviewQuote] = Field(default_factory=list)
    audience_voice_summary: str = ""

class CanonicalContent(BaseModel):
    content_id: str
    tmdb_id: int
    title: str
    original_title: Optional[str] = None
    content_type: ContentType = ContentType.MOVIE
    release_date: Optional[str] = None
    release_year: Optional[int] = None
    runtime: Optional[int] = None  # in minutes
    genres: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    overview: str = ""
    tagline: Optional[str] = None
    original_language: str = "en"
    origin_countries: List[str] = Field(default_factory=list)
    directors: List[str] = Field(default_factory=list)
    writers: List[str] = Field(default_factory=list)
    cast: List[str] = Field(default_factory=list)
    cast_detail: List[CastMemberDetail] = Field(default_factory=list)
    vote_average: float = 0.0
    vote_count: int = 0
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    gallery_images: List[str] = Field(default_factory=list)
    trailer_key: Optional[str] = None
    providers: List[StreamingProvider] = Field(default_factory=list)
    profile: Optional[ContentProfile] = None
    story_card: Optional[StoryCard] = None

class UserInteractionEvent(BaseModel):
    event_id: Optional[str] = None
    user_id: str
    session_id: Optional[str] = None
    content_id: str
    event_type: str  # "TITLE_OPEN", "TRAILER_COMPLETE", "WATCH_50_PERCENT", "WATCH_COMPLETE", "ABANDON", "LIKE", "DISLIKE", "SEARCH", "SAVE"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[float] = None

class UserTasteVector(BaseModel):
    user_id: str
    genres: Dict[str, float] = Field(default_factory=dict)
    narrative: Dict[str, float] = Field(default_factory=dict)
    emotions: Dict[str, float] = Field(default_factory=dict)
    pacing: Dict[str, float] = Field(default_factory=dict)
    international: Dict[str, float] = Field(default_factory=dict)
    preferred_directors: Dict[str, float] = Field(default_factory=dict)
    abandoned_patterns: Dict[str, float] = Field(default_factory=dict)
    interaction_count: int = 0

class UserProfile(BaseModel):
    user_id: str = "default_user"
    username: str = "Cinephile Pioneer"
    avatar_url: str = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80"
    archetype_name: str = "The Cerebral Philosopher"
    total_hours_watched: float = 48.5
    titles_watched_count: int = 24
    watchlist_count: int = 7
    top_genres: List[Dict[str, Any]] = Field(default_factory=list)
    top_directors: List[str] = Field(default_factory=list)
    taste_alignment_score: int = 94

class RecommendationIntent(BaseModel):
    mood: Optional[str] = None  # "emotional", "mystery", "reflective", "comforting", "exciting", "strange", "romance"
    energy: Optional[str] = "medium"  # "low", "medium", "high"
    max_runtime: Optional[int] = None  # e.g., 90, 120
    novelty: Optional[float] = 0.5  # 0.0 (familiar) to 1.0 (experimental/unexpected)
    avoid_tags: List[str] = Field(default_factory=list)
    preferred_regions: List[str] = Field(default_factory=list)
    target_genres: List[str] = Field(default_factory=list)
    query_text: Optional[str] = None

class RecommendationItem(BaseModel):
    content: CanonicalContent
    score: float
    personal_match_percentage: int
    match_breakdown: Dict[str, float]
    reasons: List[str]
    differences_from_usual: List[str] = Field(default_factory=list)
    contrasting_note: Optional[str] = None

class FeedbackRequest(BaseModel):
    mood: str
    content_id: str
    matched: int  # 1 for Yes, 0 for No

