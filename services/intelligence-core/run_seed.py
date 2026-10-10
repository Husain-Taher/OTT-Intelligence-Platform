import asyncio
from app.ingestion.seed_curator import seed_expanded_catalog
asyncio.run(seed_expanded_catalog())
