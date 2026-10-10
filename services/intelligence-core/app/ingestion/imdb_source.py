"""
IMDb Dataset Source for OTT Intelligence Platform.
Downloads and streams non-commercial IMDb public datasets:
- title.ratings.tsv.gz (ratings & vote counts)
- title.basics.tsv.gz (title type, year, genres, runtime)

Filters movies to identify top 5,000 to 10,000 well-known titles
based on vote count and weighted rating quality.
"""
import os
import gzip
import csv
import math
import httpx
from typing import List, Dict, Any, Optional

IMDB_RATINGS_URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"
IMDB_BASICS_URL = "https://datasets.imdbws.com/title.basics.tsv.gz"

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


class IMDbSource:
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.ratings_path = os.path.join(self.data_dir, "title.ratings.tsv.gz")
        self.basics_path = os.path.join(self.data_dir, "title.basics.tsv.gz")

    async def download_file_if_missing(self, url: str, target_path: str, client: Optional[httpx.AsyncClient] = None) -> str:
        """Downloads a gzipped dataset file if not already present on disk."""
        if os.path.exists(target_path) and os.path.getsize(target_path) > 1024:
            return target_path

        print(f"[IMDb Source] Downloading {url} -> {target_path} ...")
        close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=120.0, follow_redirects=True)
            close_client = True

        try:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                with open(target_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 64):
                        f.write(chunk)
            print(f"[IMDb Source] Download complete: {target_path} ({os.path.getsize(target_path)} bytes)")
        finally:
            if close_client:
                await client.aclose()

        return target_path

    def parse_ratings(self, min_votes: int = 10000, file_path: Optional[str] = None) -> Dict[str, Dict[str, float]]:
        """
        Parses title.ratings.tsv.gz.
        Returns a dict mapping tconst -> {'rating': float, 'votes': int, 'score': float}.
        """
        path = file_path or self.ratings_path
        if not os.path.exists(path):
            raise FileNotFoundError(f"Ratings file not found at {path}")

        ratings: Dict[str, Dict[str, float]] = {}
        with gzip.open(path, mode="rt", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            header = next(reader, None)
            # Columns: tconst, averageRating, numVotes
            for row in reader:
                if len(row) < 3:
                    continue
                tconst, avg_rating_str, num_votes_str = row[0], row[1], row[2]
                try:
                    votes = int(num_votes_str)
                    if votes < min_votes:
                        continue
                    rating = float(avg_rating_str)
                    # Quality score weighted by logarithm of vote count
                    score = rating * math.log10(votes)
                    ratings[tconst] = {"rating": rating, "votes": votes, "score": score}
                except ValueError:
                    continue
        return ratings

    def extract_top_movies(
        self,
        min_votes: int = 10000,
        limit: int = 5000,
        ratings_path: Optional[str] = None,
        basics_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Combines ratings and basics to produce ranked movie candidates.
        Only includes titleType == 'movie' and non-adult content.
        """
        ratings = self.parse_ratings(min_votes=min_votes, file_path=ratings_path)
        print(f"[IMDb Source] Parsed {len(ratings)} titles passing min_votes >= {min_votes}")

        b_path = basics_path or self.basics_path
        if not os.path.exists(b_path):
            raise FileNotFoundError(f"Basics file not found at {b_path}")

        candidates: List[Dict[str, Any]] = []
        with gzip.open(b_path, mode="rt", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            header = next(reader, None)
            # Columns: tconst, titleType, primaryTitle, originalTitle, isAdult, startYear, endYear, runtimeMinutes, genres
            for row in reader:
                if len(row) < 9:
                    continue
                tconst = row[0]
                if tconst not in ratings:
                    continue

                title_type = row[1]
                if title_type not in ["movie", "tvMovie"]:
                    continue

                is_adult = row[4]
                if is_adult == "1":
                    continue

                r_data = ratings[tconst]
                primary_title = row[2]
                year_str = row[5]
                year = int(year_str) if year_str.isdigit() else None
                runtime_str = row[7]
                runtime = int(runtime_str) if runtime_str.isdigit() else None
                genres = [g.strip() for g in row[8].split(",") if g.strip() and g != "\\N"]

                candidates.append({
                    "imdb_id": tconst,
                    "title": primary_title,
                    "year": year,
                    "runtime": runtime,
                    "genres": genres,
                    "rating": r_data["rating"],
                    "votes": r_data["votes"],
                    "score": r_data["score"]
                })

        # Rank by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:limit]
