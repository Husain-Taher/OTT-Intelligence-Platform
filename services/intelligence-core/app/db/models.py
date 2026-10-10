import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class CanonicalContentModel(Base):
    __tablename__ = "canonical_content"

    content_id = Column(String(64), primary_key=True)
    tmdb_id = Column(Integer, unique=True, index=True, nullable=True)
    imdb_id = Column(String(32), index=True, nullable=True)
    title = Column(String(512), nullable=False, index=True)
    original_title = Column(String(512), nullable=True)
    content_type = Column(String(32), default="movie")
    release_date = Column(String(32), nullable=True)
    release_year = Column(Integer, index=True, nullable=True)
    runtime = Column(Integer, nullable=True)
    genres = Column(Text, nullable=True)          # JSON array
    keywords = Column(Text, nullable=True)        # JSON array
    overview = Column(Text, nullable=True)
    tagline = Column(Text, nullable=True)
    original_language = Column(String(16), default="en")
    origin_countries = Column(Text, nullable=True) # JSON array
    directors = Column(Text, nullable=True)       # JSON array
    writers = Column(Text, nullable=True)         # JSON array
    cast_members = Column(Text, nullable=True)    # JSON array
    vote_average = Column(Float, default=0.0)
    vote_count = Column(Integer, default=0)
    poster_path = Column(Text, nullable=True)
    backdrop_path = Column(Text, nullable=True)
    trailer_key = Column(String(128), nullable=True)
    providers = Column(Text, nullable=True)       # JSON array
    profile = Column(Text, nullable=True)         # JSON ContentProfile
    cast_detail = Column(Text, nullable=True)     # JSON array of CastMemberDetail
    gallery_images = Column(Text, nullable=True)  # JSON array
    story_card = Column(Text, nullable=True)      # JSON StoryCard
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    mood_scores = relationship("ContentMoodScoreModel", back_populates="content", cascade="all, delete-orphan")


class ContentMoodScoreModel(Base):
    __tablename__ = "content_mood_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content_id = Column(String(64), ForeignKey("canonical_content.content_id", ondelete="CASCADE"), index=True, nullable=False)
    mood = Column(String(64), index=True, nullable=False)
    score = Column(Float, index=True, nullable=False)
    confidence = Column(Float, default=1.0)
    primary_cues = Column(Text, nullable=True)    # JSON list of explanation reasons
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    content = relationship("CanonicalContentModel", back_populates="mood_scores")

    __table_args__ = (
        UniqueConstraint("content_id", "mood", name="uq_content_mood"),
        Index("idx_mood_score", "mood", "score"),
    )


class ContentEmbeddingModel(Base):
    __tablename__ = "content_embeddings"

    content_id = Column(String(64), primary_key=True)
    embedding_vector = Column(Text, nullable=False)  # JSON serialized list of floats
    text_corpus = Column(Text, nullable=True)
    model_name = Column(String(128), default="all-MiniLM-L6-v2")


class ShownHistoryModel(Base):
    __tablename__ = "shown_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), index=True, nullable=False)
    content_id = Column(String(64), index=True, nullable=False)
    mood = Column(String(64), nullable=True)
    session_id = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_shown_history_user_id", "user_id", "id"),
    )


class UserEventModel(Base):
    __tablename__ = "user_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), index=True, nullable=False)
    session_id = Column(String(128), nullable=True)
    content_id = Column(String(64), nullable=False)
    event_type = Column(String(64), nullable=False)
    event_metadata = Column("metadata", Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


    __table_args__ = (
        Index("idx_user_events_user_id", "user_id", "id"),
    )


class UserTasteProfileModel(Base):
    __tablename__ = "user_taste_profiles"

    user_id = Column(String(128), primary_key=True)
    genres = Column(Text, nullable=True)
    narrative = Column(Text, nullable=True)
    emotions = Column(Text, nullable=True)
    pacing = Column(Text, nullable=True)
    international = Column(Text, nullable=True)
    preferred_directors = Column(Text, nullable=True)
    abandoned_patterns = Column(Text, nullable=True)
    interaction_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class ProfileModel(Base):
    __tablename__ = "profiles"

    user_id = Column(String(128), primary_key=True)
    display_name = Column(String(256), nullable=True)
    email = Column(String(256), nullable=True)
    picture = Column(Text, nullable=True)
    archetype = Column(String(128), nullable=True)
    onboarded = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)


class MoodCheckinModel(Base):
    __tablename__ = "mood_checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), index=True, nullable=False)
    mood = Column(String(64), nullable=False)
    genres = Column(Text, nullable=True)
    energy = Column(String(32), nullable=True)
    max_runtime = Column(Integer, nullable=True)
    novelty = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_mood_checkins_user_id", "user_id", "id"),
    )


class UserMoodAffinityModel(Base):
    __tablename__ = "user_mood_affinity"

    user_id = Column(String(128), primary_key=True)
    mood = Column(String(64), primary_key=True)
    genre = Column(String(64), primary_key=True)
    weight = Column(Float, default=0.0)
    events = Column(Integer, default=0)


class PickFeedbackModel(Base):
    __tablename__ = "pick_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), index=True, nullable=False)
    mood = Column(String(64), nullable=False)
    content_id = Column(String(64), nullable=False)
    matched = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_pick_feedback_user_id", "user_id", "id"),
    )
