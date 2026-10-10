"""
High-Throughput TMDB Ingestion & Enrichment Pipeline.
Scales catalog from initial seed to thousands of well-known titles.
Supports IMDb dataset sources, TMDB discover pagination, and curated titles.
Includes concurrency control, rate limiting, and resumable checkpointing.
"""
import os
import sys
import json
import asyncio
import argparse
from typing import List, Set, Dict, Any, Optional
from app.ingestion.tmdb_adapter import TMDBAdapter
from app.ingestion.imdb_source import IMDbSource
from app.db.database import (
    init_db, save_content, get_all_content, save_mood_scores, get_connection
)
from app.recommender.ranker import MultiStageRanker
from app.models.schemas import CanonicalContent

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
CHECKPOINT_FILE = os.path.join(DATA_DIR, "ingestion_checkpoint.json")

CORE_MOODS = ["comforting", "emotional", "reflective", "mystery", "exciting", "romance", "strange"]


class IngestionPipeline:
    def __init__(self, concurrency: int = 8, delay: float = 0.08):
        self.adapter = TMDBAdapter()
        self.imdb_source = IMDbSource()
        self.concurrency = concurrency
        self.delay = delay
        self.semaphore = asyncio.Semaphore(concurrency)
        os.makedirs(DATA_DIR, exist_ok=True)

    def load_checkpoint(self) -> Dict[str, Any]:
        if os.path.exists(CHECKPOINT_FILE):
            try:
                with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"processed_tmdb_ids": [], "processed_imdb_ids": [], "failed_ids": []}

    def save_checkpoint(self, checkpoint: Dict[str, Any]):
        try:
            with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                json.dump(checkpoint, f, indent=2)
        except Exception as e:
            print(f"[Pipeline] Warning: failed to save checkpoint: {e}")

    async def enrich_and_store(self, tmdb_id: int, imdb_id: Optional[str] = None) -> Optional[CanonicalContent]:
        """
        Fetches full TMDB payload, analyzes profile, computes all 7 mood scores,
        and persists into canonical_content and content_mood_scores.
        """
        async with self.semaphore:
            try:
                content = await self.adapter.fetch_movie_full(tmdb_id)
                if not content:
                    return None

                if imdb_id and not content.imdb_id:
                    content.imdb_id = imdb_id

                # Save canonical content
                save_content(content)

                # Compute and store mood scores for all 7 moods
                mood_scores: Dict[str, float] = {}
                cues: Dict[str, List[str]] = {}
                for m in CORE_MOODS:
                    score = MultiStageRanker.compute_mood_score(content, m)
                    mood_scores[m] = round(score, 3)

                    # Extract primary cues
                    matched_cues = []
                    for g in content.genres:
                        matched_cues.append(f"Genre: {g}")
                    if content.profile:
                        for emo, val in content.profile.emotions.items():
                            if val > 0.4:
                                matched_cues.append(f"Emotion: {emo} ({int(val*100)}%)")
                    cues[m] = matched_cues[:4]

                save_mood_scores(content.content_id, mood_scores, cues)
                await asyncio.sleep(self.delay)
                return content
            except Exception as e:
                print(f"[Pipeline] Error enriching movie {tmdb_id}: {e}")
                return None

    async def harvest_tmdb_ids(self, target_count: int = 500, min_votes: int = 300, exclude_ids: Optional[Set[int]] = None) -> List[int]:
        """
        Discovers popular and top-rated movie IDs across multiple pages, skipping already known IDs.
        """
        exclude = exclude_ids or set()
        collected_ids: Set[int] = set()
        page = 1
        max_pages = min(500, max(20, (target_count // 10) + 15))

        print(f"[Pipeline] Harvesting up to {target_count} new movie IDs from TMDB...")
        while len(collected_ids) < target_count and page <= max_pages:
            try:
                top_ids = await self.adapter.get_top_rated_movie_ids(page=page)
                pop_ids = await self.adapter.get_popular_movie_ids(page=page)
                for mid in top_ids + pop_ids:
                    if mid not in exclude and mid not in collected_ids:
                        collected_ids.add(mid)
                        if len(collected_ids) >= target_count:
                            break
                page += 1
                await asyncio.sleep(0.04)
            except Exception as e:
                print(f"[Pipeline] Discover page {page} error: {e}")
                break

        print(f"[Pipeline] Harvested {len(collected_ids)} new candidate movie IDs across {page - 1} pages.")
        return list(collected_ids)[:target_count]


    async def run(
        self,
        source: str = "tmdb",
        limit: int = 200,
        min_votes: int = 5000,
        batch_size: int = 25
    ) -> Dict[str, Any]:
        """
        Executes the ingestion pipeline.
        """
        init_db()
        checkpoint = self.load_checkpoint()
        processed_set: Set[int] = set(checkpoint.get("processed_tmdb_ids", []))

        # Check what is already stored in the DB
        existing = get_all_content()
        for item in existing:
            processed_set.add(item.tmdb_id)

        target_tmdb_ids: List[int] = []
        imdb_map: Dict[int, str] = {}

        if source == "imdb":
            print(f"[Pipeline] Extracting top movies from IMDb (min_votes={min_votes}, limit={limit})...")
            try:
                candidates = self.imdb_source.extract_top_movies(min_votes=min_votes, limit=limit)
                print(f"[Pipeline] Resolving {len(candidates)} IMDb IDs to TMDB...")
                for c in candidates:
                    iid = c["imdb_id"]
                    mid = await self.adapter.find_by_imdb_id(iid)
                    if mid:
                        target_tmdb_ids.append(mid)
                        imdb_map[mid] = iid
                    await asyncio.sleep(0.03)
            except Exception as e:
                print(f"[Pipeline] IMDb source error: {e}, falling back to TMDB discover")
                source = "tmdb"

        if source == "tmdb":
            target_tmdb_ids = await self.harvest_tmdb_ids(target_count=limit, exclude_ids=processed_set)


        to_process = [mid for mid in target_tmdb_ids if mid not in processed_set][:limit]
        print(f"[Pipeline] Ready to ingest {len(to_process)} new titles ({len(processed_set)} already present).")

        successful = 0
        failed = 0

        # Process in batches with progress logging
        for i in range(0, len(to_process), batch_size):
            batch = to_process[i:i + batch_size]
            tasks = [self.enrich_and_store(mid, imdb_map.get(mid)) for mid in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for mid, res in zip(batch, results):
                if isinstance(res, CanonicalContent) and res is not None:
                    successful += 1
                    processed_set.add(mid)
                    checkpoint["processed_tmdb_ids"].append(mid)
                else:
                    failed += 1
                    checkpoint["failed_ids"].append(mid)

            self.save_checkpoint(checkpoint)
            total_db = len(get_all_content())
            print(f"[Pipeline Batch {i//batch_size + 1}] Progress: {successful} added, {failed} failed. Total DB catalog: {total_db}")

        return {
            "source": source,
            "processed": len(to_process),
            "successful": successful,
            "failed": failed,
            "total_catalog": len(get_all_content())
        }


def main():
    parser = argparse.ArgumentParser(description="OTT Intelligence Catalog Ingestion Pipeline")
    parser.add_argument("--source", choices=["tmdb", "imdb"], default="tmdb", help="Candidate data source")
    parser.add_argument("--limit", type=int, default=50, help="Number of titles to ingest")
    parser.add_argument("--min-votes", type=int, default=5000, help="Minimum IMDb/TMDB votes")
    parser.add_argument("--concurrency", type=int, default=8, help="Concurrent workers")
    args = parser.parse_args()

    pipeline = IngestionPipeline(concurrency=args.concurrency)
    result = asyncio.run(pipeline.run(source=args.source, limit=args.limit, min_votes=args.min_votes))
    print("\n=== PIPELINE RUN FINISHED ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
