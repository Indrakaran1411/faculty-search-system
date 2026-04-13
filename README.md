# 🎓 Faculty Information Retrieval System

> Intelligent academic profile search using **Hybrid BM25 + Semantic Search**, Entity Resolution, and multi-source data aggregation — **100% free, runs locally, no API keys needed**.

---

## 📋 Problem Statement

Design and develop a **scalable system** that, given a faculty or professor's name as input, can:

- ✅ **Accurately identify** the correct individual *(disambiguation)*
- ✅ **Retrieve relevant information** from multiple heterogeneous sources
- ✅ **Extract and structure key attributes** such as:
  - 🖼 Profile image
  - 👤 Name
  - 🏛 University and department
  - 📍 Location
  - 🔬 Research areas
  - 📧 Contact details (email, phone)
  - 📚 Publications
  - 🔗 Academic profiles (Google Scholar, ORCID, etc.)
- ✅ **Deliver results in real-time** with high accuracy and low latency
- ✅ **Handle challenges** like noisy data, duplicate entries, and incomplete information

---

## 📁 Project Structure

```
FacultySearchSystem/
├── backend/
│   ├── main.py                 ← FastAPI server (port 8000)
│   ├── services/
│   │   ├── scraper.py          ← Multi-source async data fetcher
│   │   ├── search_engine.py    ← Hybrid BM25 + Semantic Search (RRF)
│   │   ├── entity_resolver.py  ← Name disambiguation & deduplication
│   │   ├── profile_builder.py  ← Structured profile output & cleaning
│   │   └── llm_service.py      ← AI summarization & RAG-based Q&A
│   └── utils/
│       └── cache.py            ← Disk-based caching (no Redis needed)
├── frontend-vite/
│   └── src/
│       ├── components/
│       │   ├── ProfileCard.jsx ← Faculty profile display card
│       │   ├── AIBox.jsx       ← AI summary + chat interface
│       │   ├── SearchBar.jsx   ← Search input with filters
│       │   └── ResultsList.jsx ← Results grid with metadata
│       ├── pages/
│       │   └── SearchPage.jsx  ← Main search page
│       ├── utils/
│       │   └── api.js          ← API client (fetch, summarize, ask)
│       ├── App.jsx             ← Root component with header/footer
│       └── App.css             ← Full design system & styles
├── data/                       ← Auto-created: cache, indexes
├── docs/
│   ├── architecture.md         ← System architecture details
│   └── PROBLEM_STATEMENT.md    ← Full problem statement with pipeline
├── requirements.txt            ← Python dependencies
├── setup.sh                    ← One-time setup script
└── run.sh                      ← Start both backend + frontend
```

---

## ⚡ Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- 4 GB RAM *(for sentence-transformer model)*

### 1. Setup *(run once)*
```bash
chmod +x setup.sh run.sh
./setup.sh
```

### 2. Run
```bash
./run.sh
```

Then open **http://localhost:5173** in your browser.

#### Or run separately:
```bash
# Terminal 1 — Backend
source venv/bin/activate
cd backend
python main.py

# Terminal 2 — Frontend
cd frontend-vite
npm run dev
```

---

## 🔍 How It Works

### System Pipeline

```
User Input (Faculty Name + optional Affiliation / Research Area)
         │
         ▼
  Name Variant Generation
  (abbreviations, hyphens, middle names)
         │
         ▼
  ┌─────────────────────────────────────────┐
  │         Multi-Source Scraper            │
  │  OpenAlex · Semantic Scholar · ORCID   │
  │        · Google Scholar (fallback)      │
  └─────────────────────────────────────────┘
         │  (async, concurrent, 5s timeout)
         ▼
  Entity Resolver
  (name similarity > 82%, affiliation + publication overlap)
         │
         ▼
  Profile Builder
  (clean, validate, normalize all fields)
         │
         ▼
  ┌─────────────────────────────────┐
  │     Hybrid Search Engine        │
  │  BM25 (40%) + Semantic (60%)   │
  │   via Reciprocal Rank Fusion    │
  └─────────────────────────────────┘
         │
         ▼
  AI Research Summarizer (top 5 profiles)
         │
         ▼
  Ranked Profiles → REST API → React Frontend
```

### Data Sources *(all free, no keys required)*

| Source | What It Provides |
|--------|-----------------|
| **OpenAlex API** | Research concepts, affiliations, citation stats, publications |
| **Semantic Scholar API** | Papers, citations, author disambiguation, ORCID link |
| **ORCID Public API** | Verified employment, department, location, publications |
| **Google Scholar** *(fallback)* | Profile image, h-index, i10-index, top publications |

### Hybrid Search
| Component | Weight | Description |
|-----------|--------|-------------|
| **BM25** (rank-bm25) | 40% | Keyword precision for exact name/affiliation matches |
| **Sentence Transformers** (MiniLM-L6-v2, ~90 MB) | 60% | Semantic similarity scoring |
| **Reciprocal Rank Fusion** | Fusion | Combines BM25 + semantic scores for final ranking |

### Entity Resolution
Profiles from different sources merge into one if:
- Name similarity **> 82%** (SequenceMatcher)
- **Affiliation overlap** — shared institution keywords
- **Publication overlap** — shared paper titles

### Key Attributes Extracted

| Attribute | Sources |
|-----------|---------|
| Profile Image | Google Scholar |
| Name | All sources |
| University & Department | ORCID, Semantic Scholar, OpenAlex, webpage scraping |
| Location | ORCID, OpenAlex, DuckDuckGo faculty page search |
| Research Areas | OpenAlex (topics + x_concepts), Google Scholar interests |
| Email | ORCID, homepage scraping, Google Scholar |
| Phone | Homepage scraping (regex patterns) |
| Publications | All sources (sorted by citation count) |
| Google Scholar Link | Google Scholar direct scrape |
| ORCID Link | ORCID API, Semantic Scholar externalIds |
| OpenAlex Link | OpenAlex API |
| Semantic Scholar Link | Semantic Scholar API |

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/search?name=...` | Main faculty search |
| `GET` | `/search?name=...&affiliation=MIT` | Filtered search by institution |
| `GET` | `/search?name=...&research_area=NLP` | Filtered by research area |
| `GET` | `/search/status?search_id=...` | Poll enrichment status |
| `GET` | `/profile/{scholar_id}` | Fetch by Google Scholar ID |
| `GET` | `/health` | System health & index stats |
| `GET` | `/docs` | Swagger interactive docs |
| `POST` | `/ai/summarize` | Generate AI research summary |
| `POST` | `/ai/ask` | RAG-based Q&A on a profile |
| `DELETE` | `/cache` | Clear disk cache |

### Example
```bash
curl "http://localhost:8000/search?name=Andrew+Ng&affiliation=Stanford"
```

---

## 🤖 AI Features

### Research Summary
- Automatically generated for the top 5 results
- Uses structured NLG (no large model download required)
- Displays with a real-time typewriter animation in the UI

### Ask AI (RAG Q&A)
- Converts each faculty profile into factual text chunks
- Retrieves relevant chunks via **FAISS + cosine similarity**
- Falls back to keyword-intent detection for common questions
- Suggested questions: *"What does this professor research?"*, *"How many citations?"*, etc.

---

## 🧩 Libraries Used

| Library | Purpose |
|---------|---------|
| `fastapi` + `uvicorn` | Backend REST API server |
| `aiohttp` + `asyncio` | Concurrent async HTTP requests |
| `sentence-transformers` | Free local embeddings (MiniLM-L6-v2) |
| `faiss-cpu` | Vector similarity search (RAG retrieval) |
| `rank-bm25` | BM25 keyword scoring |
| `beautifulsoup4` | HTML parsing for homepage scraping |
| `diskcache` | Local disk caching (no Redis) |
| `spacy` | NER and text processing |
| `requests` | Synchronous HTTP for Google Scholar |
| React + Vite | Frontend UI framework |

---

## ⚠️ Notes

- **First run**: The sentence-transformer model (~90 MB) downloads automatically on first use.
- **Google Scholar**: May be rate-limited after many requests. The system gracefully falls back to OpenAlex, ORCID, and Semantic Scholar.
- **Response time**: ~3–8 seconds on first query (live scraping). Cached queries return in **< 1 second**.
- **Background enrichment**: After initial results return, the system asynchronously scrapes faculty homepages to find email, phone, department, and courses — then updates the cache.
- **Cache**: Stored in `data/cache/`. Delete this folder to reset all cached results.

---

## 🔮 Extending the System

| Extension | How |
|-----------|-----|
| Distributed caching | Replace `DiskCache` with `redis-py` |
| Larger BM25 index | Add `Elasticsearch` backend |
| Knowledge graph linking | Add `Neo4j` for entity disambiguation at scale |
| True LLM summarization | Integrate Ollama (free local LLM) |
| More university sources | Add scrapers for faculty directory pages |
| PDF/CV parsing | Add `pdfplumber` for uploaded CVs |

---

## 📊 Evaluation

```bash
# Run from backend/
python -c "
from services.search_engine import HybridSearchEngine
engine = HybridSearchEngine()
# Compare BM25-only vs hybrid on a test set
"
```

---

## 📄 Documentation

| Document | Description |
|----------|-------------|
| [docs/PROBLEM_STATEMENT.md](docs/PROBLEM_STATEMENT.md) | Full problem statement with pipeline diagram and success criteria |
| [docs/architecture.md](docs/architecture.md) | System architecture & design decisions |
| [http://localhost:8000/docs](http://localhost:8000/docs) | Live Swagger API documentation |
