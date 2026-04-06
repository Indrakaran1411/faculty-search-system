"""
Profile Router — /profile endpoints
"""

from fastapi import APIRouter, HTTPException
import logging

from ..services.scraper import FacultyScraper
from ..services.profile_builder import ProfileBuilder
from ..utils.cache import DiskCache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/profile", tags=["Profile"])

scraper = FacultyScraper()
profile_builder = ProfileBuilder()
cache = DiskCache()


@router.get(
    "/{scholar_id}",
    summary="Get full profile by Google Scholar ID",
    description="Fetches and returns a complete faculty profile using a Google Scholar author ID."
)
async def get_profile_by_id(scholar_id: str):
    cache_key = f"profile_{scholar_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        raw = await scraper.fetch_by_scholar_id(scholar_id)
        if not raw:
            raise HTTPException(status_code=404, detail=f"Profile '{scholar_id}' not found")
        result = profile_builder.build(raw)
        cache.set(cache_key, result, ttl=7200)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile fetch error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
