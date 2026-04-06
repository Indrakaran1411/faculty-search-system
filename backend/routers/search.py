"""
Search Router — /search and /profile endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from ..services.scraper import FacultyScraper
from ..services.search_engine import HybridSearchEngine
from ..services.entity_resolver import EntityResolver
from ..services.profile_builder import ProfileBuilder
from ..utils.cache import DiskCache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["Search"])

# Shared service instances (injected from main.py via app.state)
scraper = FacultyScraper()
search_engine = HybridSearchEngine()
entity_resolver = EntityResolver()
profile_builder = ProfileBuilder()
cache = DiskCache()


@router.get(
    "",
    summary="Search faculty by name",
    description="Returns ranked, structured faculty profiles from multiple free academic sources."
)
async def search_faculty(
    name: str = Query(..., min_length=2, description="Faculty member name"),
    affiliation: Optional[str] = Query(None, description="University or institution"),
    research_area: Optional[str] = Query(None, description="Research domain"),
    limit: int = Query(5, ge=1, le=20)
):
    cache_key = f"search_{name}_{affiliation}_{research_area}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        logger.info(f"[Cache HIT] {name}")
        return cached

    logger.info(f"[Search] name={name!r} affiliation={affiliation!r}")

    try:
        raw_profiles = await scraper.fetch_all(name, affiliation, research_area)
        if not raw_profiles:
            raise HTTPException(status_code=404, detail=f"No profiles found for '{name}'")

        resolved = entity_resolver.resolve(raw_profiles, name, affiliation)
        profiles = [profile_builder.build(p) for p in resolved[:limit]]
        query = f"{name} {affiliation or ''} {research_area or ''}".strip()
        ranked = search_engine.rank(profiles, query)

        result = {
            "query": {"name": name, "affiliation": affiliation, "research_area": research_area},
            "count": len(ranked),
            "profiles": ranked
        }
        cache.set(cache_key, result, ttl=3600)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
