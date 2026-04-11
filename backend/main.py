"""
Faculty Information Retrieval System
FastAPI backend entry point — imports routers, registers middleware
"""

import logging
import sys
import os
import asyncio
import re
from copy import deepcopy

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
SEARCH_MEMORY_TTL_SECONDS = 30 * 24 * 3600
BACKGROUND_ENRICH_LIMIT = 10

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
active_enrichments = set()


def _normalize_search_text(value: Optional[str]) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _search_memory_key(name: str, affiliation: Optional[str], research_area: Optional[str]) -> str:
    return "search_memory::" + "::".join([
        _normalize_search_text(name),
        _normalize_search_text(affiliation),
        _normalize_search_text(research_area),
    ])


def _name_variants(name: str) -> list[str]:
    base = (name or "").strip()
    variants = []
    candidates = [
        base,
        base.replace("-", " "),
        base.replace(".", " "),
    ]
    tokens = [token for token in re.split(r"[\s\-]+", base) if token]
    if len(tokens) >= 2:
        candidates.append(" ".join(tokens))
        candidates.append(f"{tokens[0]} {tokens[-1]}")
    for candidate in candidates:
        cleaned = re.sub(r"\s+", " ", candidate).strip()
        if cleaned and cleaned not in variants:
            variants.append(cleaned)
    return variants[:4]


def _affiliation_variants(affiliation: Optional[str]) -> list[Optional[str]]:
    if not affiliation:
        return [None]
    base = affiliation.strip()
    lowered = base.lower()
    aliases = {
        "iitm": ["IIT Madras", "Indian Institute of Technology Madras"],
        "iitd": ["IIT Delhi", "Indian Institute of Technology Delhi"],
        "iitb": ["IIT Bombay", "Indian Institute of Technology Bombay"],
        "iitk": ["IIT Kanpur", "Indian Institute of Technology Kanpur"],
        "iisc": ["Indian Institute of Science", "IISc Bangalore"],
        "mit": ["Massachusetts Institute of Technology", "MIT"],
        "stanford": ["Stanford University"],
    }
    variants = [base]
    for key, values in aliases.items():
        if lowered == key or lowered in {value.lower() for value in values}:
            variants.extend(values)
    deduped = []
    for variant in variants:
        cleaned = variant.strip()
        if cleaned and cleaned not in deduped:
            deduped.append(cleaned)
    return deduped[:4]


def _dedupe_raw_profiles(raw_profiles: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for profile in raw_profiles:
        key = (
            profile.get("source", ""),
            profile.get("orcid_id", "") or profile.get("orcid_url", ""),
            profile.get("openalex_url", ""),
            profile.get("semantic_scholar_url", ""),
            profile.get("scholar_id", ""),
            _normalize_search_text(profile.get("name", "")),
            _normalize_search_text((profile.get("affiliations") or [""])[0]),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(profile)
    return deduped


async def _fetch_profiles_with_fallbacks(name: str, affiliation: Optional[str], research_area: Optional[str]) -> list[dict]:
    attempts = []
    for name_variant in _name_variants(name):
        for affiliation_variant in _affiliation_variants(affiliation):
            attempts.append((name_variant, affiliation_variant))

    raw_profiles = []
    for index, (name_variant, affiliation_variant) in enumerate(attempts):
        fetched = await scraper.fetch_all(name_variant, affiliation_variant, research_area)
        if fetched:
            raw_profiles.extend(fetched)
            raw_profiles = _dedupe_raw_profiles(raw_profiles)
        if raw_profiles and (len(raw_profiles) >= 20 or index >= 1):
            break
    return raw_profiles


async def _enrich_and_store(cache_key: str, memory_key: str, result: dict):
    try:
        profiles = deepcopy(result.get("profiles", []))
        enriched = await asyncio.gather(*(scraper.enrich_profile(profile) for profile in profiles[:BACKGROUND_ENRICH_LIMIT]))
        profiles[:len(enriched)] = enriched
        result["profiles"] = profiles
        result["count"] = len(profiles)
        result["enrichment_status"] = "complete"
        cache.set(cache_key, result, ttl=3600)
        cache.set(memory_key, result, ttl=SEARCH_MEMORY_TTL_SECONDS)
    except Exception as e:
        logger.warning(f"Background enrichment failed for {cache_key}: {e}")
        result["enrichment_status"] = "failed"
        cache.set(cache_key, result, ttl=3600)
        cache.set(memory_key, result, ttl=SEARCH_MEMORY_TTL_SECONDS)
    finally:
        active_enrichments.discard(cache_key)


def _has_meaningful_profile_data(profile: dict) -> bool:
    metrics = profile.get("metrics", {})
    return any([
        profile.get("designation"),
        profile.get("university"),
        profile.get("department"),
        profile.get("location"),
        profile.get("email"),
        profile.get("phone"),
        profile.get("homepage"),
        profile.get("research_areas"),
        profile.get("course_works"),
        profile.get("publications"),
        profile.get("affiliations"),
        any(metrics.get(key, 0) > 0 for key in ("citations", "h_index", "i10_index", "paper_count")),
    ])


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
    limit: int = Query(20, ge=1, le=50)
):
    cache_key = f"search_{name}_{affiliation}_{research_area}_{limit}"
    memory_key = _search_memory_key(name, affiliation, research_area)
    cached = cache.get(cache_key)
    if cached:
        logger.info(f"[Cache HIT] {name}")
        return cached

    logger.info(f"[Search] name={name!r} affiliation={affiliation!r}")

    try:
        raw_profiles = await _fetch_profiles_with_fallbacks(name, affiliation, research_area)
        if not raw_profiles:
            logger.warning("Initial source fetch returned no profiles; retrying once.")
            raw_profiles = await _fetch_profiles_with_fallbacks(name, affiliation, research_area)
        if not raw_profiles:
            remembered = cache.get(memory_key)
            if remembered:
                logger.info(f"[Memory HIT] {name}")
                remembered["memory_fallback"] = True
                remembered["profiles"] = remembered.get("profiles", [])[:limit]
                remembered["count"] = len(remembered["profiles"])
                remembered["search_id"] = cache_key
                remembered["enrichment_status"] = "complete"
                return remembered
            raise HTTPException(status_code=404, detail=f"No profiles found for '{name}'")

        resolved = entity_resolver.resolve(raw_profiles, name, affiliation)
        profiles = [profile_builder.build(p) for p in resolved]
        profiles = [p for p in profiles if _has_meaningful_profile_data(p)]
        if not profiles:
            raise HTTPException(status_code=404, detail=f"No detailed profiles found for '{name}'")
        query = f"{name} {affiliation or ''} {research_area or ''}".strip()
        ranked = search_engine.rank(profiles, query)[:limit]

        result = {
            "query": {"name": name, "affiliation": affiliation, "research_area": research_area},
            "count": len(ranked),
            "profiles": ranked,
            "memory_fallback": False,
            "search_id": cache_key,
            "enrichment_status": "pending",
        }
        cache.set(cache_key, result, ttl=3600)
        cache.set(memory_key, result, ttl=SEARCH_MEMORY_TTL_SECONDS)
        if cache_key not in active_enrichments:
            active_enrichments.add(cache_key)
            asyncio.create_task(_enrich_and_store(cache_key, memory_key, deepcopy(result)))
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        remembered = cache.get(memory_key)
        if remembered:
            logger.info(f"[Memory RECOVERY] {name}")
            remembered["memory_fallback"] = True
            remembered["profiles"] = remembered.get("profiles", [])[:limit]
            remembered["count"] = len(remembered["profiles"])
            remembered["search_id"] = cache_key
            remembered["enrichment_status"] = "complete"
            return remembered
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search/status", tags=["Search"])
def search_status(search_id: str):
    cached = cache.get(search_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Search status not found")
    return cached


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
