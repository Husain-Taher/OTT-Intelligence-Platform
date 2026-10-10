import asyncio
from typing import List, Set
from app.ingestion.tmdb_adapter import TMDBAdapter
from app.db.database import init_db, save_content, get_all_content

# Curated high-impact titles across all emotional, narrative, and pacing archetypes
CURATED_FLAGSHIP_MOVIES = [
    # Sci-Fi / Cosmos / Mind Benders
    157336,  # Interstellar
    27205,   # Inception
    335984,  # Blade Runner 2049
    329865,  # Arrival
    152601,  # Her
    438631,  # Dune
    693134,  # Dune: Part Two
    603,     # The Matrix
    545611,  # Everything Everywhere All at Once
    77,      # Memento
    1124,    # The Prestige
    550,     # Fight Club
    244786,  # Whiplash

    # Psychological Thriller / Crime / Dark Mystery
    496243,  # Parasite (KR)
    11423,   # Memories of Murder (KR)
    670,     # Oldboy (KR)
    705996,  # Decision to Leave (KR)
    1949,    # Zodiac
    146233,  # Prisoners
    546554,  # Knives Out
    807,     # Se7en
    11324,   # Shutter Island
    210577,  # Gone Girl
    274,     # The Silence of the Lambs
    915935,  # Anatomy of a Fall (FR)
    582,     # The Lives of Others (DE)

    # Emotional Drama / Deep Resonance
    334543,  # Manchester by the Sea
    666277,  # Past Lives
    531428,  # Portrait of a Lady on Fire (FR)
    758866,  # Drive My Car (JP)
    38,      # Eternal Sunshine of the Spotless Mind
    76,      # Before Sunrise
    278,     # The Shawshank Redemption
    238,     # The Godfather
    11216,   # Cinema Paradiso (IT)
    598,     # City of God (BR)
    497814,  # Shoplifters (JP)

    # Comfort / Light / Wholesome / Joy
    120467,  # The Grand Budapest Hotel
    194,     # Amélie (FR)
    346648,  # Paddington 2
    129,     # Spirited Away (JP)
    8392,    # My Neighbor Totoro (JP)
    10315,   # Fantastic Mr. Fox
    212778,  # Chef
    637,     # Life Is Beautiful (IT)
    372058,  # Your Name. (JP)

    # Kinetic Action / High Tension / Spectacle
    76341,   # Mad Max: Fury Road
    155,     # The Dark Knight
    361743,  # Top Gun: Maverick
    579974,  # RRR (IN)
    534780,  # Andhadhun (IN)
    245891,  # John Wick
    98,      # Gladiator
    324857,  # Spider-Man: Into the Spider-Verse
    460465,  # Ride Your Wave

    # Masterpieces of Indian Cinema & Bollywood
    20453,   # 3 Idiots (Rajkumar Hirani, Aamir Khan, R. Madhavan, Kareena Kapoor)
    360814,  # Dangal (Aamir Khan, Mahavir Singh Phogat)
    117691,  # Gangs of Wasseypur - Part 1 (Anurag Kashyap, Manoj Bajpayee, Nawazuddin)
    126400,  # Gangs of Wasseypur - Part 2 (Anurag Kashyap, Nawazuddin Siddiqui)
    15774,   # Swades (Ashutosh Gowariker, Shah Rukh Khan)
    19404,   # Dilwale Dulhania Le Jayenge (Shah Rukh Khan, Kajol)
    14163,   # Chak De! India (Shah Rukh Khan)
    872906,  # Jawan (Shah Rukh Khan, Deepika Padukone, Nayanthara)
    348892,  # Bajrangi Bhaijaan (Kabir Khan, Salman Khan, Kareena Kapoor Khan)
    61202,   # Zindagi Na Milegi Dobara (Zoya Akhtar, Hrithik Roshan, Katrina Kaif)
    297222,  # PK (Rajkumar Hirani, Aamir Khan, Anushka Sharma)
    7508,    # Taare Zameen Par (Aamir Khan, Darsheel Safary)
    538858,  # Tumbbad (Rahi Anil Barve, Sohum Shah)
    352173,  # Drishyam (Nishikant Kamat, Ajay Devgn, Tabu)
    256040,  # Baahubali: The Beginning (S.S. Rajamouli, Prabhas, Rana Daggubati)
    491625,  # Gully Boy (Zoya Akhtar, Ranveer Singh, Alia Bhatt)
    597089,  # Article 15 (Anubhav Sinha, Ayushmann Khurrana)
    858485,  # Kantara (Rishab Shetty)
    598826,  # Sardar Udham (Shoojit Sircar, Vicky Kaushal)
    332835,  # Piku (Shoojit Sircar, Amitabh Bachchan, Deepika Padukone, Irrfan Khan)
    191714,  # The Lunchbox (Ritesh Batra, Irrfan Khan, Nimrat Kaur)
    127501,  # Barfi! (Anurag Basu, Ranbir Kapoor, Priyanka Chopra)
    743563,  # Vikram (Lokesh Kanagaraj, Kamal Haasan, Vijay Sethupathi, Fahadh Faasil)
    19666,   # Lagaan (Ashutosh Gowariker, Aamir Khan)
]

CURATED_FLAGSHIP_TV = [
    70523,   # Dark (DE - Sci-Fi Mystery)
    1396,    # Breaking Bad (Character Transformation)
    60059,   # Better Call Saul (Slow Burn Character Study)
    94605,   # Arcane (Animation / High Atmosphere)
    87108,   # Chernobyl (Historical Tension)
    93405,   # Squid Game (KR - Survival Suspense)
    76479,   # The Boys (Satire Action)
    85552,   # Euphoria (Teen Drama / Visual Style)
    100088,  # The Last of Us (Post-apocalyptic Drama)
    46648,   # True Detective (Atmospheric Crime)
    67744,   # Mindhunter (Psychological Profiling)
]

async def seed_expanded_catalog():
    init_db()
    adapter = TMDBAdapter()
    print("=== BEGINNING EXPANDED CATALOG INGESTION WITH VIDEO TRAILERS ===")

    existing_items = get_all_content()
    existing_tmdb_ids: Set[int] = set(item.tmdb_id for item in existing_items)
    print(f"Catalog currently has {len(existing_items)} titles.")

    # 1. Ingest Curated Flagship Movies
    for tmdb_id in CURATED_FLAGSHIP_MOVIES:
        if tmdb_id in existing_tmdb_ids:
            # Re-fetch if trailer_key might be missing
            existing = next((i for i in existing_items if i.tmdb_id == tmdb_id), None)
            if existing and existing.trailer_key:
                continue
        try:
            print(f"Fetching movie ID {tmdb_id} with trailer...")
            content = await adapter.fetch_movie_full(tmdb_id)
            if content:
                save_content(content)
                existing_tmdb_ids.add(tmdb_id)
                print(f" Saved: {content.title} ({content.release_year}) [Trailer: {content.trailer_key or 'None'}]")
            await asyncio.sleep(0.12)
        except Exception as e:
            print(f"Error fetching movie {tmdb_id}: {e}")

    # 2. Ingest Curated TV Shows
    for tmdb_id in CURATED_FLAGSHIP_TV:
        existing = next((i for i in existing_items if i.tmdb_id == tmdb_id), None)
        if existing and existing.trailer_key:
            continue
        try:
            print(f"Fetching TV ID {tmdb_id} with trailer...")
            content = await adapter.fetch_tv_full(tmdb_id)
            if content:
                save_content(content)
                existing_tmdb_ids.add(tmdb_id)
                print(f" Saved: {content.title} [Series] [Trailer: {content.trailer_key or 'None'}]")
            await asyncio.sleep(0.12)
        except Exception as e:
            print(f"Error fetching TV {tmdb_id}: {e}")

    # 3. Ingest Popular & Top-Rated Movies from TMDB for deep variety
    try:
        popular_ids = await adapter.get_popular_movie_ids(page=1)
        top_ids = await adapter.get_top_rated_movie_ids(page=1)
        all_new_ids = list(set(popular_ids + top_ids) - existing_tmdb_ids)[:30]

        print(f"Ingesting {len(all_new_ids)} trending & top-rated titles...")
        for mid in all_new_ids:
            try:
                content = await adapter.fetch_movie_full(mid)
                if content:
                    save_content(content)
                    print(f" Ingested: {content.title} ({content.release_year}) [{', '.join(content.genres[:2])}]")
                await asyncio.sleep(0.12)
            except Exception as e:
                pass
    except Exception as e:
        print(f"Bulk ingestion note: {e}")

    total = len(get_all_content())
    print(f"\n Catalog Expansion Complete! Total database catalog: {total} titles.")

if __name__ == "__main__":
    asyncio.run(seed_expanded_catalog())
