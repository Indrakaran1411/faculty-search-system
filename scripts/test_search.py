#!/usr/bin/env python3
"""
test_search.py — CLI test script for the Faculty Search backend
Run from the project root:
    python scripts/test_search.py "Andrew Ng"
    python scripts/test_search.py "Geoffrey Hinton" --affiliation "University of Toronto"
    python scripts/test_search.py "Yoshua Bengio" --research-area "deep learning"
"""

import sys
import asyncio
import argparse
import json
import time

# Allow running from project root
sys.path.insert(0, "backend")

from services.scraper import FacultyScraper
from services.search_engine import HybridSearchEngine
from services.entity_resolver import EntityResolver
from services.profile_builder import ProfileBuilder


def print_profile(profile: dict, rank: int):
    sep = "─" * 60
    print(f"\n{sep}")
    print(f"  #{rank}  {profile.get('name', 'Unknown')}")
    print(sep)

    if profile.get("university"):
        print(f"  🏛  {profile['university']}")
    if profile.get("department"):
        print(f"  🏢  {profile['department']}")
    if profile.get("email"):
        print(f"  📧  {profile['email']}")
    if profile.get("location"):
        print(f"  📍  {profile['location']}")

    m = profile.get("metrics", {})
    if any(m.get(k, 0) > 0 for k in ["citations", "h_index", "paper_count"]):
        print(f"\n  📊  Citations: {m.get('citations', 0):,}  |  "
              f"h-index: {m.get('h_index', 0)}  |  "
              f"Papers: {m.get('paper_count', 0)}")

    areas = profile.get("research_areas", [])
    if areas:
        print(f"\n  🔬  Research: {', '.join(areas[:5])}")

    links = profile.get("academic_profiles", {})
    if links:
        print(f"\n  🔗  Profiles:")
        for name, url in links.items():
            if url:
                print(f"       {name:20s} {url}")

    pubs = profile.get("publications", [])
    if pubs:
        print(f"\n  📚  Top publications:")
        for p in pubs[:3]:
            year = f"({p['year']})" if p.get("year") else ""
            cite = f"[{p['citations']} citations]" if p.get("citations", 0) > 0 else ""
            print(f"       • {p['title'][:70]}... {year} {cite}")

    sources = profile.get("sources", [])
    print(f"\n  ✅  Sources: {', '.join(sources)}")
    score = profile.get("relevance_score", 0)
    if score:
        print(f"  🎯  Relevance score: {score:.4f}")


async def run_search(name: str, affiliation: str = None, research_area: str = None):
    print(f"\n{'='*60}")
    print(f"  Faculty Search — Query: \"{name}\"")
    if affiliation:
        print(f"  Affiliation filter:    \"{affiliation}\"")
    if research_area:
        print(f"  Research area filter:  \"{research_area}\"")
    print(f"{'='*60}")

    scraper = FacultyScraper()
    search_engine = HybridSearchEngine()
    entity_resolver = EntityResolver()
    profile_builder = ProfileBuilder()

    search_engine.load_or_build_index()

    print("\n⏳ Fetching from sources (Google Scholar, ORCID, OpenAlex, Semantic Scholar)...")
    t0 = time.time()

    raw = await scraper.fetch_all(name, affiliation, research_area)
    print(f"   Raw profiles fetched: {len(raw)}")

    if not raw:
        print("\n❌ No profiles found. Try a different name or affiliation.")
        return

    resolved = entity_resolver.resolve(raw, name, affiliation)
    print(f"   After entity resolution: {len(resolved)} unique profiles")

    profiles = [profile_builder.build(p) for p in resolved[:5]]
    query = f"{name} {affiliation or ''} {research_area or ''}".strip()
    ranked = search_engine.rank(profiles, query)

    elapsed = time.time() - t0
    print(f"\n✅ Search completed in {elapsed:.2f}s")
    print(f"   Returning top {len(ranked)} results\n")

    for i, profile in enumerate(ranked, 1):
        print_profile(profile, i)

    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Faculty Search CLI — test the backend without the frontend"
    )
    parser.add_argument("name", help="Faculty member name to search for")
    parser.add_argument("--affiliation", "-a", default=None, help="Filter by university/institution")
    parser.add_argument("--research-area", "-r", default=None, help="Filter by research domain")
    parser.add_argument("--json", "-j", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    if args.json:
        # JSON output mode
        async def json_mode():
            scraper = FacultyScraper()
            entity_resolver = EntityResolver()
            profile_builder = ProfileBuilder()
            search_engine = HybridSearchEngine()
            search_engine.load_or_build_index()

            raw = await scraper.fetch_all(args.name, args.affiliation, args.research_area)
            resolved = entity_resolver.resolve(raw, args.name, args.affiliation)
            profiles = [profile_builder.build(p) for p in resolved[:5]]
            query = f"{args.name} {args.affiliation or ''} {args.research_area or ''}".strip()
            ranked = search_engine.rank(profiles, query)
            print(json.dumps(ranked, indent=2, default=str))

        asyncio.run(json_mode())
    else:
        asyncio.run(run_search(args.name, args.affiliation, args.research_area))


if __name__ == "__main__":
    main()
