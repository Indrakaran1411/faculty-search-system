# 🎓 Faculty Information Retrieval System — Problem Statement

---

## Problem Statement

Design and develop a **scalable system** that, given a faculty or professor's name as input, can:

- **Accurately identify** the correct individual *(disambiguation)*
- **Retrieve relevant information** from multiple heterogeneous sources
- **Extract and structure key attributes** such as:
  - Profile image
  - Name
  - University and department
  - Location
  - Research areas
  - Contact details (email, phone)
  - Publications
  - Academic profiles (Google Scholar, ORCID, etc.)
- **Deliver results in real-time** with high accuracy and low latency
- **Handle challenges** like noisy data, duplicate entries, and incomplete information

---

## Objectives

### 1. Disambiguation
Accurately identify the **correct individual** when multiple people share the same or similar names across different institutions and data sources.

**How it's solved:**
- Entity Resolution using **name similarity > 82%** (SequenceMatcher)
- **Affiliation overlap** — shared institution tokens
- **Publication overlap** — shared paper titles across sources
- **Hybrid Search scoring** (BM25 + Semantic) ranks the most relevant match first

### 2. Multi-Source Data Retrieval
Retrieve relevant information from **multiple heterogeneous sources**, including:

| Source | Data Provided |
|--------|--------------|
| **OpenAlex API** | Research concepts, affiliations, citation stats, publications |
| **Semantic Scholar API** | Papers, citations, author disambiguation, ORCID link |
| **ORCID Public API** | Verified employment, department, location, publications |
| **Google Scholar** *(fallback)* | Profile image, h-index, i10-index, top publications |
| **Faculty Homepages** | Phone, office location, courses taught |

### 3. Key Attribute Extraction & Structuring

The system extracts and structures the following for every faculty profile:

| Attribute | Description | Sources |
|-----------|-------------|---------|
| 🖼 **Profile Image** | Faculty photo | Google Scholar |
| 👤 **Name** | Full, cleaned name | All sources |
| 🏛 **University** | Institution name | ORCID, OpenAlex, Semantic Scholar |
| 🏢 **Department** | Academic department | ORCID, homepage scraping |
| 📍 **Location** | City/country or office | ORCID, OpenAlex, homepage scraping |
| 🔬 **Research Areas** | Domains of expertise | OpenAlex topics, Google Scholar interests |
| 📧 **Email** | Contact email | ORCID, Google Scholar, homepage |
| 📞 **Phone** | Office/mobile number | Homepage regex scraping |
| 📚 **Publications** | Title, year, venue, citations | All sources (sorted by citations) |
| 🔗 **Google Scholar** | Profile link | Google Scholar direct scrape |
| 🔗 **ORCID** | Verified researcher ID | ORCID API / Semantic Scholar |
| 🔗 **OpenAlex** | OpenAlex author page | OpenAlex API |
| 🔗 **Semantic Scholar** | Research profile link | Semantic Scholar API |

### 4. Real-Time Delivery
- **First query**: ~3–8 seconds (live async scraping from 3–4 sources in parallel)
- **Cached queries**: < 1 second (disk-based cache with 30-day memory)
- **Background enrichment**: Initial results returned instantly; profiles enriched asynchronously

---

## Challenges Addressed

| Challenge | How the System Handles It |
|-----------|--------------------------|
| **Noisy Data** | Regex validation, field normalization (`_clean_email`, `_clean_url`), and HTML stripping |
| **Duplicate Entries** | Entity Resolution merges profiles from different sources using name + affiliation + publication fingerprinting |
| **Incomplete Information** | Multi-source fallback strategy; graceful `—` display for missing fields; background homepage scraping fills gaps |
| **Name Ambiguity** | Hybrid BM25 + Semantic Search with Reciprocal Rank Fusion (RRF) scores the best match |
| **Rate Limiting** | Google Scholar is used only as last resort; disk cache prevents redundant API calls |
| **Slow Sources** | Async `asyncio.wait()` with a 5-second timeout cancels slow tasks; results are returned from whichever sources respond first |

---

## System Architecture

```
User Input: Faculty Name  [+ optional: Affiliation, Research Area]
                │
                ▼
   ┌────────────────────────┐
   │  Name Variant Generator │  → Handles "A.K. Singh" → "Amit Singh", hyphenations, etc.
   └────────────────────────┘
                │
                ▼
   ┌─────────────────────────────────────────────────┐
   │             Multi-Source Scraper                │
   │                                                 │
   │  ┌─────────────┐  ┌──────────────┐  ┌───────┐  │
   │  │  OpenAlex   │  │   Semantic   │  │  ORCID│  │  ← all run concurrently (asyncio)
   │  │    API      │  │  Scholar API │  │  API  │  │
   │  └─────────────┘  └──────────────┘  └───────┘  │
   │              ↓ fallback only ↓                  │
   │         ┌──────────────────┐                    │
   │         │  Google Scholar  │                    │
   │         │  (direct scrape) │                    │
   │         └──────────────────┘                    │
   └─────────────────────────────────────────────────┘
                │  raw profiles (possibly 20–50 records)
                ▼
   ┌──────────────────────┐
   │   Deduplication      │  → Removes exact duplicates by source+id+name fingerprint
   └──────────────────────┘
                │
                ▼
   ┌──────────────────────┐
   │   Entity Resolver    │  → Merges profiles of the same person across sources
   │  (name + affil +     │     using similarity scoring
   │   publication match) │
   └──────────────────────┘
                │
                ▼
   ┌──────────────────────┐
   │   Profile Builder    │  → Cleans, validates, and structures all fields
   │  (clean + normalize) │     into a consistent schema
   └──────────────────────┘
                │
                ▼
   ┌──────────────────────────────────────┐
   │        Hybrid Search Engine          │
   │                                      │
   │  BM25 Score (40%)                    │
   │  + Sentence Transformer Score (60%)  │
   │  → Reciprocal Rank Fusion → Ranking  │
   └──────────────────────────────────────┘
                │
                ├──→ AI Research Summarizer (top 5 profiles)
                │         └─ Template NLG: fast, no LLM download needed
                │
                ▼
   ┌──────────────────────────────────────┐
   │  Async Background Enrichment         │
   │  • DuckDuckGo faculty page search    │
   │  • Homepage scraping for phone,      │
   │    department, office, courses       │
   └──────────────────────────────────────┘
                │
                ▼
        REST API (FastAPI)
                │
                ▼
        React Frontend (Vite)
        ┌────────────────────────────────────────┐
        │  ProfileCard                           │
        │  ┌──── Header: Avatar + Name + Badges  │
        │  ├──── Metrics: Citations, h-index     │
        │  ├──── Contact & Location column       │
        │  ├──── Research Areas column           │
        │  ├──── Academic Profile Links          │
        │  ├──── AI Summary (typewriter effect)  │
        │  ├──── Ask AI (RAG chat)               │
        │  └──── Publications list               │
        └────────────────────────────────────────┘
```

---

## Scalability Considerations

| Concern | Current Solution | At Scale |
|---------|-----------------|---------|
| **Caching** | Disk-based (`diskcache`) | Replace with Redis |
| **Search Index** | FAISS in-memory | Replace with Elasticsearch |
| **Scraping concurrency** | `asyncio` + `aiohttp` | Add worker pool / task queue (Celery) |
| **API** | Single FastAPI process | Horizontal scaling behind load balancer |
| **Entity Graph** | In-memory resolution | Neo4j knowledge graph |

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Disambiguation accuracy | > 90% correct identification on common names |
| First-query latency | < 8 seconds |
| Cached query latency | < 1 second |
| Source coverage | ≥ 2 sources per profile |
| Field completeness (email, university, research areas) | > 70% of results |
| Profile image availability | > 50% of results (via Google Scholar) |
