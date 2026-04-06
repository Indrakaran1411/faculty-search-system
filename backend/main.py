"""
Faculty Information Retrieval System
FastAPI backend entry point — imports routers, registers middleware
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from services.scraper import FacultyScraper
from services.search_engine import HybridSearchEngine
from services.entity_resolver import EntityResolver
from services.profile_builder import ProfileBuilder
from utils.cache import DiskCache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Faculty Information Retrieval System",
    description=(
        "Intelligent faculty search using Hybrid BM25 + Semantic Search, "
        "Entity Resolution, and multi-source aggregation. "
        "100% free — no API keys required."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Allow all origins so Vite (port 5173) and any other frontend can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

scraper = FacultyScraper()
search_engine = HybridSearchEngine()
entity_resolver = EntityResolver()
profile_builder = ProfileBuilder()
cache = DiskCache()


@app.on_event("startup")
async def startup():
    logger.info("Starting Faculty Search System...")
    search_engine.load_or_build_index()
    logger.info("System ready.")


@app.get("/", tags=["System"])
def root():
    return {
        "name": "Faculty Information Retrieval System",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", tags=["System"])
def health():
    return {
        "status": "ok",
        "index_size": search_engine.index_size(),
        "cache_entries": cache.size(),
        "version": "1.0.0"
    }


@app.get("/search", tags=["Search"])
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


@app.get("/profile/{scholar_id}", tags=["Profile"])
async def get_profile_by_id(scholar_id: str):
    cache_key = f"profile_{scholar_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    try:
        raw = await scraper.fetch_by_scholar_id(scholar_id)
        if not raw:
            raise HTTPException(status_code=404, detail="Profile not found")
        result = profile_builder.build(raw)
        cache.set(cache_key, result, ttl=7200)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/cache", tags=["System"])
def clear_cache():
    cache.clear()
    return {"message": "Cache cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)