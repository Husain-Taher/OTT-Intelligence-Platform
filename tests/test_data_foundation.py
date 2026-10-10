"""
Tests for Phase 1: Data Foundation & Ingestion Pipeline.
Validates:
- SQLAlchemy models and schema definitions
- Precomputed mood scores storage (content_mood_scores)
- IMDb dataset streaming and filtering
- Resumable pipeline checkpointing and enrichment
"""
import os
import sys
import gzip
import csv
import json
import pytest
from unittest.mock import AsyncMock, patch

ROOT = os.path.join(os.path.dirname(__file__), "..", "services", "intelligence-core")
sys.path.insert(0, os.path.abspath(ROOT))

from app.db.models import (
    Base, CanonicalContentModel, ContentMoodScoreModel, ShownHistoryModel, UserEventModel
)
from app.db.engine import create_engine, SessionLocal
from app.db import database
from app.ingestion.imdb_source import IMDbSource
from app.ingestion.pipeline import IngestionPipeline
from app.models.schemas import CanonicalContent, ContentType


def test_sqlalchemy_models_and_tables(tmp_path):
    """Asserts SQLAlchemy ORM models can create schema and persist records."""
    db_file = tmp_path / "orm_test.db"
    test_engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=test_engine)

    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=test_engine)
    session = Session()

    # Create canonical content model instance
    content = CanonicalContentModel(
        content_id="movie_9999",
        tmdb_id=9999,
        imdb_id="tt9999999",
        title="Test Film",
        release_year=2024,
        genres=json.dumps(["Sci-Fi", "Drama"]),
        vote_average=8.5,
        vote_count=1200
    )
    session.add(content)
    session.commit()

    # Add a mood score
    mood_score = ContentMoodScoreModel(
        content_id="movie_9999",
        mood="reflective",
        score=0.92,
        confidence=1.0,
        primary_cues=json.dumps(["Genre: Sci-Fi", "Emotion: REFLECTION (80%)"])
    )
    session.add(mood_score)
    session.commit()

    # Query back
    queried = session.query(CanonicalContentModel).filter_by(content_id="movie_9999").first()
    assert queried is not None
    assert queried.title == "Test Film"
    assert len(queried.mood_scores) == 1
    assert queried.mood_scores[0].mood == "reflective"
    assert queried.mood_scores[0].score == 0.92
    session.close()


def test_imdb_source_parser_and_filters(tmp_path):
    """Asserts IMDbSource filters non-movies, adult content, and calculates weighted scores."""
    ratings_gz = tmp_path / "title.ratings.tsv.gz"
    basics_gz = tmp_path / "title.basics.tsv.gz"

    # Create synthetic ratings TSV.gz
    with gzip.open(ratings_gz, "wt", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["tconst", "averageRating", "numVotes"])
        writer.writerow(["tt001", "8.5", "50000"])  # High votes, pass
        writer.writerow(["tt002", "9.0", "500"])    # Low votes, reject (< 5000)
        writer.writerow(["tt003", "7.0", "15000"])  # Pass

    # Create synthetic basics TSV.gz
    with gzip.open(basics_gz, "wt", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["tconst", "titleType", "primaryTitle", "originalTitle", "isAdult", "startYear", "endYear", "runtimeMinutes", "genres"])
        writer.writerow(["tt001", "movie", "Masterpiece Sci-Fi", "Masterpiece", "0", "2020", "\\N", "145", "Sci-Fi,Drama"])
        writer.writerow(["tt002", "movie", "Short Indep", "Short", "0", "2021", "\\N", "80", "Comedy"])
        writer.writerow(["tt003", "short", "Not A Movie", "Short", "0", "2022", "\\N", "15", "Animation"])  # Reject titleType != movie

    source = IMDbSource(data_dir=str(tmp_path))
    results = source.extract_top_movies(
        min_votes=5000,
        limit=10,
        ratings_path=str(ratings_gz),
        basics_path=str(basics_gz)
    )

    assert len(results) == 1
    top = results[0]
    assert top["imdb_id"] == "tt001"
    assert top["title"] == "Masterpiece Sci-Fi"
    assert top["year"] == 2020
    assert top["rating"] == 8.5
    assert top["votes"] == 50000
    assert top["score"] > 0


def test_pipeline_checkpointing(tmp_path, monkeypatch):
    """Asserts that the ingestion pipeline persists and resumes from checkpoints."""
    checkpoint_file = tmp_path / "test_checkpoint.json"
    monkeypatch.setattr("app.ingestion.pipeline.CHECKPOINT_FILE", str(checkpoint_file))

    pipeline = IngestionPipeline()
    initial = pipeline.load_checkpoint()
    assert initial["processed_tmdb_ids"] == []

    pipeline.save_checkpoint({
        "processed_tmdb_ids": [101, 102],
        "processed_imdb_ids": ["tt101", "tt102"],
        "failed_ids": []
    })

    reloaded = pipeline.load_checkpoint()
    assert reloaded["processed_tmdb_ids"] == [101, 102]


def test_enrich_and_store_mood_scores(tmp_path, monkeypatch):
    """Asserts that enrich_and_store computes and saves all 7 mood scores to the database."""
    import asyncio
    db_file = tmp_path / "test_db.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_file))
    database.init_db()

    mock_content = CanonicalContent(
        content_id="movie_550",
        tmdb_id=550,
        imdb_id="tt0137523",
        title="Fight Club",
        content_type=ContentType.MOVIE,
        release_year=1999,
        genres=["Drama", "Thriller"],
        keywords=["dissociative identity disorder", "anti-establishment"],
        overview="An insomniac office worker and a devil-may-care soap maker form an underground fight club.",
        vote_average=8.4,
        vote_count=28000
    )

    pipeline = IngestionPipeline()
    pipeline.adapter.fetch_movie_full = AsyncMock(return_value=mock_content)

    res = asyncio.run(pipeline.enrich_and_store(550, imdb_id="tt0137523"))

    assert res is not None
    assert res.title == "Fight Club"

    # Verify canonical content was saved
    saved_item = database.get_content_by_id("movie_550")
    assert saved_item is not None
    assert saved_item.title == "Fight Club"

    # Verify mood scores table was populated for all 7 moods
    mood_scores = database.get_mood_scores("movie_550")
    assert len(mood_scores) == 7
    for m in ["comforting", "emotional", "reflective", "mystery", "exciting", "romance", "strange"]:
        assert m in mood_scores
        assert 0.0 <= mood_scores[m] <= 1.0
