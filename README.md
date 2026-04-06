# 🎓 Faculty Information Retrieval System

Intelligent academic profile search using **Hybrid BM25 + Semantic Search**, Entity Resolution, and multi-source data aggregation — **100% free, runs locally, no API keys needed**.

---

## 📁 Project Structure

```
faculty_search/
├── backend/
│   ├── main.py            ← FastAPI server (port 8000)
│   ├── scraper.py         ← Multi-source data fetcher
│   ├── search_engine.py   ← Hybrid BM25 + Semantic search
│   ├── entity_resolver.py ← Name disambiguation & deduplication
│   ├── profile_builder.py ← Structured profile output
│   └── cache.py           ← Disk-based caching (no Redis needed)
├── frontend/
│   ├── src/
│   │   ├── App.js         ← React UI
│   │   └── App.css        ← Styling
│   └── public/index.html
├── data/                  ← Auto-created: cache, indexes
├── requirements.txt       ← Python dependencies
├── setup.sh               ← One-time setup script
└── run.sh                 ← Start both backend + frontend
```

---

## ⚡ Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- 4GB RAM (for sentence transformer model)

### 1. Setup (run once)
```bash
cd faculty_search
chmod +x setup.sh run.sh
./setup.sh
```

### 2. Run
```bash
./run.sh
```

Then open **http://localhost:3000** in your browser.

Or run separately:
```bash
# Terminal 1 — Backend
source venv/bin/activate
cd backend
python main.py

# Terminal 2 — Frontend
cd frontend
npm start
```

---

## 🔍 How It Works

### Data Sources (all free)
| Source | What it provides |
|--------|-----------------|
| **Google Scholar** (scholarly) | Profile image, citations, h-index, publications |
| **ORCID Public API** | Verified employment, publications, ORCID ID |
| **OpenAlex API** | Research concepts, affiliation, citation stats |
| **Semantic Scholar API** | Papers, citations, author disambiguation |

### Search Pipeline
```
Query → Entity Resolution → Hybrid Search → Ranked Profiles
             ↓                    ↓
      Name disambiguation    BM25 + Semantic
      Affiliation matching   Score Fusion (RRF)
      Publication overlap
```

### Hybrid Search
- **BM25** (rank-bm25): keyword precision for exact name/affiliation matches
- **Sentence Transformers** (all-MiniLM-L6-v2, ~90MB): semantic similarity
- **Reciprocal Rank Fusion**: combines both scores (40% BM25 + 60% semantic)

### Entity Resolution
Profiles from different sources are merged into one if:
- Name similarity > 82% (SequenceMatcher)
- Affiliation overlap (shared institution keywords)
- Publication overlap (shared paper titles)

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/search?name=...` | Main search |
| GET | `/search?name=...&affiliation=MIT` | Filtered search |
| GET | `/profile/{scholar_id}` | Fetch by Scholar ID |
| GET | `/health` | System status |
| GET | `/docs` | Swagger UI |

### Example
```bash
curl "http://localhost:8000/search?name=Andrew+Ng&affiliation=Stanford"
```

---

## 🧩 Free Libraries Used

| Library | Purpose |
|---------|---------|
| `fastapi` + `uvicorn` | Backend API server |
| `scholarly` | Google Scholar scraping |
| `sentence-transformers` | Free local embeddings (MiniLM) |
| `faiss-cpu` | Vector similarity search |
| `rank-bm25` | BM25 keyword scoring |
| `spacy` | NER and text processing |
| `beautifulsoup4` | HTML parsing |
| `diskcache` | Local disk caching (no Redis) |
| `aiohttp` | Async HTTP requests |
| React | Frontend UI |

---

## ⚠️ Notes

- **First run**: The sentence transformer model (~90MB) downloads automatically on first use.
- **Google Scholar**: May be rate-limited after many requests. The system gracefully falls back to other sources.
- **Response time**: ~3-8 seconds on first query (scraping live). Subsequent identical queries are cached and return in <1 second.
- **Cache**: Stored in `data/cache/`. Delete this folder to clear all cached results.

---

## 🔮 Extending the System

- Add **Redis** for distributed caching: replace `DiskCache` with `redis-py`
- Add **Elasticsearch** for larger-scale BM25 indexing
- Add **Neo4j** for knowledge graph entity linking
- Add **LLM summarization**: use Ollama (free local LLM) for research summaries
- Scrape **university department pages** for phone numbers and office locations

---

## 📊 Evaluation

To benchmark against traditional keyword search:
```python
# Run from backend/
python -c "
from search_engine import HybridSearchEngine
engine = HybridSearchEngine()
# Compare BM25-only vs hybrid on your test set
"
```
