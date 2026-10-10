import os
import httpx
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from app.models.schemas import CanonicalContent, ContentType, StreamingProvider, CastMemberDetail, StoryCard
from app.intelligence.nlp_review_analyzer import analyze_review_corpus

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "9f28b17c76c356100ffb5d0257449d80")
BASE_URL = "https://api.themoviedb.org/3"

class TMDBAdapter:
    def __init__(self, api_key: str = TMDB_API_KEY):
        self.api_key = api_key
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "OTT-Intelligence-Engine/1.0"
        }

    async def fetch_movie_full(self, tmdb_id: int) -> Optional[CanonicalContent]:
        url = f"{BASE_URL}/movie/{tmdb_id}"
        params = {
            "api_key": self.api_key,
            "append_to_response": "credits,keywords,watch/providers,reviews,videos,images",
            "language": "en-US"
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return self._parse_movie_payload(data)

    async def fetch_tv_full(self, tmdb_id: int) -> Optional[CanonicalContent]:
        url = f"{BASE_URL}/tv/{tmdb_id}"
        params = {
            "api_key": self.api_key,
            "append_to_response": "credits,keywords,watch/providers,reviews,videos,images",
            "language": "en-US"
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return self._parse_tv_payload(data)

    async def get_popular_movie_ids(self, page: int = 1) -> List[int]:
        url = f"{BASE_URL}/movie/popular"
        params = {"api_key": self.api_key, "language": "en-US", "page": page}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code != 200:
                return []
            return [m["id"] for m in resp.json().get("results", [])]

    async def get_top_rated_movie_ids(self, page: int = 1) -> List[int]:
        url = f"{BASE_URL}/movie/top_rated"
        params = {"api_key": self.api_key, "language": "en-US", "page": page}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code != 200:
                return []
            return [m["id"] for m in resp.json().get("results", [])]

    async def get_trending_tv_ids(self, page: int = 1) -> List[int]:
        url = f"{BASE_URL}/trending/tv/week"
        params = {"api_key": self.api_key, "language": "en-US", "page": page}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code != 200:
                return []
            return [m["id"] for m in resp.json().get("results", [])]

    async def discover_by_genre(self, genre_id: int, page: int = 1) -> List[int]:
        url = f"{BASE_URL}/discover/movie"
        params = {
            "api_key": self.api_key,
            "with_genres": str(genre_id),
            "sort_by": "popularity.desc",
            "vote_count.gte": 150,
            "page": page
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code != 200:
                return []
            return [m["id"] for m in resp.json().get("results", [])]

    async def find_by_imdb_id(self, imdb_id: str) -> Optional[int]:
        """Looks up a TMDB movie id using an external IMDb ID (e.g. tt0111161)."""
        url = f"{BASE_URL}/find/{imdb_id}"
        params = {"api_key": self.api_key, "external_source": "imdb_id"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code != 200:
                return None
            results = resp.json().get("movie_results", [])
            if results:
                return results[0]["id"]
            # Also check tv_results if applicable
            tv_results = resp.json().get("tv_results", [])
            if tv_results:
                return tv_results[0]["id"]
            return None

    def _parse_movie_payload(self, data: Dict[str, Any]) -> CanonicalContent:

        tmdb_id = data.get("id")
        title = data.get("title", "")
        original_title = data.get("original_title")
        release_date = data.get("release_date")
        release_year = int(release_date.split("-")[0]) if release_date and "-" in release_date else None
        runtime = data.get("runtime")
        genres = [g["name"] for g in data.get("genres", [])]
        
        # Keywords
        kw_data = data.get("keywords", {}).get("keywords", [])
        keywords = [k["name"] for k in kw_data]

        overview = data.get("overview", "")
        tagline = data.get("tagline")
        original_language = data.get("original_language", "en")
        origin_countries = data.get("origin_country", [])

        # Credits with profile photos
        credits_data = data.get("credits", {})
        cast = [c["name"] for c in credits_data.get("cast", [])[:6]]
        cast_detail: List[CastMemberDetail] = [
            CastMemberDetail(
                name=c.get("name", ""),
                character=c.get("character"),
                profile_path=f"https://image.tmdb.org/t/p/w300{c['profile_path']}" if c.get("profile_path") else None
            )
            for c in credits_data.get("cast", [])[:8] if c.get("name")
        ]
        crew = credits_data.get("crew", [])
        directors = [c["name"] for c in crew if c.get("job") == "Director"]
        writers = [c["name"] for c in crew if c.get("job") in ["Writer", "Screenplay", "Author"]][:3]

        # Gallery images (backdrops)
        images_data = data.get("images", {})
        gallery_images: List[str] = [
            f"https://image.tmdb.org/t/p/original{b['file_path']}"
            for b in images_data.get("backdrops", [])[:8] if b.get("file_path")
        ]

        # Trailer Video
        videos = data.get("videos", {}).get("results", [])
        trailer_key = next((v["key"] for v in videos if v.get("site") == "YouTube" and v.get("type") in ["Trailer", "Teaser"]), None)
        if not trailer_key and videos:
            trailer_key = next((v["key"] for v in videos if v.get("site") == "YouTube"), None)

        # Watch Providers
        wp_data = data.get("watch/providers", {}).get("results", {})
        providers: List[StreamingProvider] = []
        for region in ["US", "GB", "IN", "KR", "FR", "DE"]:
            if region in wp_data:
                for flat in wp_data[region].get("flatrate", []):
                    p = StreamingProvider(
                        provider_id=flat["provider_id"],
                        provider_name=flat["provider_name"],
                        logo_path=f"https://image.tmdb.org/t/p/original{flat['logo_path']}" if flat.get("logo_path") else None,
                        type="flatrate"
                    )
                    if not any(existing.provider_id == p.provider_id for existing in providers):
                        providers.append(p)

        # Reviews
        raw_reviews = [
            {"author": r.get("author", "Viewer"), "content": r.get("content", "")}
            for r in data.get("reviews", {}).get("results", [])
        ]

        # Analyze profile
        profile = analyze_review_corpus(
            title=title,
            overview=overview,
            genres=genres,
            keywords=keywords,
            raw_reviews=raw_reviews
        )

        poster_path = f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get("poster_path") else None
        backdrop_path = f"https://image.tmdb.org/t/p/original{data.get('backdrop_path')}" if data.get("backdrop_path") else None
        if backdrop_path and backdrop_path not in gallery_images:
            gallery_images.insert(0, backdrop_path)

        story_card = StoryCard(
            thematic_pillars=[g for g in genres[:3]] or ["Cinematic Storytelling", "Human Ambition"],
            opening_hook=overview[:140] + "..." if overview else "A high-stakes premise immediately commands attention.",
            midpoint_escalation="Dramatic tensions compound as conflicting loyalties and stakes escalate.",
            climax_payoff="An unforgettable sequence delivering immense narrative and sensory catharsis.",
            notable_dialogue=f"\"{tagline}\"" if tagline else None,
            visual_style_note=f"Pioneering visual framing and lighting with an immersive {original_language.upper()} cinematic aesthetic."
        )

        return CanonicalContent(
            content_id=f"movie_{tmdb_id}",
            tmdb_id=tmdb_id,
            imdb_id=data.get("imdb_id"),
            title=title,
            original_title=original_title,

            content_type=ContentType.MOVIE,
            release_date=release_date,
            release_year=release_year,
            runtime=runtime,
            genres=genres,
            keywords=keywords,
            overview=overview,
            tagline=tagline,
            original_language=original_language,
            origin_countries=origin_countries,
            directors=directors,
            writers=writers,
            cast=cast,
            cast_detail=cast_detail,
            vote_average=data.get("vote_average", 0.0),
            vote_count=data.get("vote_count", 0),
            poster_path=poster_path,
            backdrop_path=backdrop_path,
            gallery_images=gallery_images,
            trailer_key=trailer_key,
            providers=providers,
            profile=profile,
            story_card=story_card
        )

    def _parse_tv_payload(self, data: Dict[str, Any]) -> CanonicalContent:
        tmdb_id = data.get("id")
        title = data.get("name", "")
        original_title = data.get("original_name")
        first_air = data.get("first_air_date")
        release_year = int(first_air.split("-")[0]) if first_air and "-" in first_air else None
        genres = [g["name"] for g in data.get("genres", [])]
        kw_data = data.get("keywords", {}).get("results", [])
        keywords = [k["name"] for k in kw_data]
        overview = data.get("overview", "")
        tagline = data.get("tagline")
        original_language = data.get("original_language", "en")
        origin_countries = data.get("origin_country", [])

        credits_data = data.get("credits", {})
        cast = [c["name"] for c in credits_data.get("cast", [])[:6]]
        crew = credits_data.get("crew", [])
        directors = [c["name"] for c in crew if c.get("job") in ["Director", "Executive Producer"]][:2]
        writers = [c["name"] for c in crew if c.get("job") in ["Writer", "Creator"]][:2]

        videos = data.get("videos", {}).get("results", [])
        trailer_key = next((v["key"] for v in videos if v.get("site") == "YouTube" and v.get("type") in ["Trailer", "Teaser"]), None)
        if not trailer_key and videos:
            trailer_key = next((v["key"] for v in videos if v.get("site") == "YouTube"), None)

        wp_data = data.get("watch/providers", {}).get("results", {})
        providers: List[StreamingProvider] = []
        for region in ["US", "GB"]:
            if region in wp_data:
                for flat in wp_data[region].get("flatrate", []):
                    p = StreamingProvider(
                        provider_id=flat["provider_id"],
                        provider_name=flat["provider_name"],
                        logo_path=f"https://image.tmdb.org/t/p/original{flat['logo_path']}" if flat.get("logo_path") else None,
                        type="flatrate"
                    )
                    if not any(existing.provider_id == p.provider_id for existing in providers):
                        providers.append(p)

        raw_reviews = [
            {"author": r.get("author", "Viewer"), "content": r.get("content", "")}
            for r in data.get("reviews", {}).get("results", [])
        ]

        profile = analyze_review_corpus(
            title=title,
            overview=overview,
            genres=genres,
            keywords=keywords,
            raw_reviews=raw_reviews
        )

        poster_path = f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get("poster_path") else None
        backdrop_path = f"https://image.tmdb.org/t/p/original{data.get('backdrop_path')}" if data.get("backdrop_path") else None

        return CanonicalContent(
            content_id=f"tv_{tmdb_id}",
            tmdb_id=tmdb_id,
            title=title,
            original_title=original_title,
            content_type=ContentType.SERIES,
            release_date=first_air,
            release_year=release_year,
            runtime=data.get("episode_run_time", [50])[0] if data.get("episode_run_time") else 50,
            genres=genres,
            keywords=keywords,
            overview=overview,
            tagline=tagline,
            original_language=original_language,
            origin_countries=origin_countries,
            directors=directors,
            writers=writers,
            cast=cast,
            vote_average=data.get("vote_average", 0.0),
            vote_count=data.get("vote_count", 0),
            poster_path=poster_path,
            backdrop_path=backdrop_path,
            trailer_key=trailer_key,
            providers=providers,
            profile=profile
        )
