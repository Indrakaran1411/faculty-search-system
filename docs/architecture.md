# System Architecture

## Overview

The Faculty Information Retrieval System uses a **two-pipeline architecture** (offline + online) combined with **hybrid search** (BM25 + semantic embeddings) to retrieve and rank faculty profiles from multiple free academic data sources.

---

## Data Flow

```
User Query (name + optional affiliation/research area)
        │
        ▼
┌─────────────────────────────────┐
│         ONLINE PIPELINE         │
│                                 │
│  1. Parallel source fetching    │  ← Google Scholar, ORCID,
│     (async HTTP, ~3-8s)         │     OpenAlex, Semantic Scholar
│                                 │
│  2. Entity Resolution           │  ← Name similarity + affiliation
│     (dedup + merge)             │     overlap + publication overlap
│                                 │
│  3. Profile Building            │  ← Clean, structure, normalize
│                                 │
│  4. Hybrid Ranking              │  ← BM25 (40%) + Semantic (60%)
│     (RRF fusion)                │     via Reciprocal Rank Fusion
│                                 │
│  5. Disk Cache (diskcache)      │  ← TTL: 1hr search, 2hr profiles
└─────────────────────────────────┘
        │
        ▼
Structured Faculty Profile JSON
```

---

## Component Responsibilities

### `backend/services/scraper.py`
Fetches raw faculty data from 4 free sources in parallel using `asyncio.gather`:

| Source | Library/API | Data provided |
|--------|-------------|---------------|
| Google Scholar | `scholarly` (PyPI) | Photo, h-index, citations, interests, publications |
| ORCID | Public REST API | Verified employment, publications, ORCID ID |
| OpenAlex | Public REST API | Research concepts, institution, citation stats |
| Semantic Scholar | Public REST API | Papers, author disambiguation, citation counts |

### `backend/services/entity_resolver.py`
Deduplicates and merges profiles that refer to the same person.

**Similarity signals used:**
1. **Name similarity** — SequenceMatcher ratio (threshold: 0.82)
2. **Affiliation overlap** — shared institution keywords
3. **Publication overlap** — shared paper title prefixes

**Merge strategy:** Source priority: Google Scholar > Semantic Scholar > OpenAlex > ORCID. Takes max of numeric metrics, union of list fields, deduplicates publications by title.

### `backend/services/search_engine.py`
Hybrid ranking using two complementary methods:

```
BM25 Score (keyword)     Semantic Score (embedding)
      │                         │
      ▼                         ▼
  RRF rank                  RRF rank
      │                         │
      └──── weighted sum ────────┘
            (40% BM25 + 60% semantic)
                    │
                    ▼
           Final ranked list
```

- **BM25**: `rank-bm25` library, tokenises profile text (name + affiliation + research areas + publication titles)
- **Semantic**: `sentence-transformers` with `all-MiniLM-L6-v2` model (~90MB, downloads once), FAISS cosine similarity
- **RRF**: Reciprocal Rank Fusion with k=60, combines both rank lists

### `backend/services/profile_builder.py`
Normalises raw merged data into the final API schema:
- Extracts primary university from affiliation list
- Cleans email, homepage URLs
- Builds academic profile link map
- Deduplicates and sorts publications by citation count
- Generates a plain-text research summary

### `backend/utils/cache.py`
Disk-based cache using `diskcache` (no Redis needed).
- Search results cached for 1 hour
- Individual profiles cached for 2 hours
- Cache stored in `data/cache/`

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | System info |
| GET | `/health` | Status, index size, cache size |
| GET | `/search?name=...` | Main search |
| GET | `/search?name=...&affiliation=...` | Filtered search |
| GET | `/profile/{scholar_id}` | Full profile by Scholar ID |
| DELETE | `/cache` | Clear disk cache |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc UI |

---

## Frontend Architecture

```
App.js
  ├── Header (inline)
  ├── SearchPage (pages/)
  │     ├── SearchBar (components/)
  │     ├── ResultsList (components/)
  │     │     └── ProfileCard (components/) × N
  │     └── EmptyState (components/)
  └── Footer (inline)

hooks/
  └── useSearch.js   — fetch logic, loading/error state

utils/
  └── api.js         — API_BASE, fetchFaculty(), fetchProfileById()
```

---

## Performance Characteristics

| Scenario | Latency |
|----------|---------|
| First query (cold, scraping live) | 3–8 seconds |
| Cached query (same name repeated) | < 100ms |
| Semantic model first load | ~2s (model already on disk) |
| BM25 scoring (5–10 profiles) | < 10ms |

---

## Extending the System

### Add Redis caching
Replace `DiskCache` in `utils/cache.py`:
```python
import redis
r = redis.Redis(host="localhost", port=6379, db=0)
```

### Add Elasticsearch for large-scale BM25
```python
from elasticsearch import Elasticsearch
es = Elasticsearch("http://localhost:9200")
```

### Add local LLM summarization (Ollama, free)
```bash
ollama pull mistral
```
```python
import requests
resp = requests.post("http://localhost:11434/api/generate", json={
    "model": "mistral",
    "prompt": f"Summarize the research of: {profile['name']}. Areas: {profile['research_areas']}"
})
```

### Add a Knowledge Graph (Neo4j Community, free)
```python
from neo4j import GraphDatabase
driver = GraphDatabase.driver("bolt://localhost:7687")
```
