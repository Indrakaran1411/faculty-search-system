"""
Hybrid Search Engine
- BM25 keyword ranking (rank_bm25, free)
- Semantic similarity with Sentence Transformers (free local model)
- FAISS vector index (free, local)
- Reciprocal Rank Fusion (RRF) for score combination
"""

import os
import json
import logging
import pickle
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path
from math import log10

logger = logging.getLogger(__name__)

INDEX_PATH = Path("data/search_index.pkl")


class HybridSearchEngine:
    def __init__(self):
        self.bm25 = None
        self.faiss_index = None
        self.embeddings_model = None
        self.indexed_profiles = []
        self._model_loaded = False
        self._index_size = 0

    def _load_model(self):
        if self._model_loaded:
            return
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence transformer model (all-MiniLM-L6-v2)...")
            # Free, local model — downloads once (~90MB)
            self.embeddings_model = SentenceTransformer("all-MiniLM-L6-v2")
            self._model_loaded = True
            logger.info("Sentence transformer loaded.")
        except Exception as e:
            logger.warning(f"Sentence transformer not available: {e}")

    def load_or_build_index(self):
        """Load existing index from disk or start fresh."""
        self._load_model()
        if INDEX_PATH.exists():
            try:
                with open(INDEX_PATH, "rb") as f:
                    data = pickle.load(f)
                    self.indexed_profiles = data.get("profiles", [])
                    self._index_size = len(self.indexed_profiles)
                    logger.info(f"Loaded existing index with {self._index_size} profiles")
                    if self.indexed_profiles:
                        self._rebuild_bm25()
            except Exception as e:
                logger.warning(f"Could not load index: {e}")

    def _profile_to_text(self, profile: Dict) -> str:
        """Convert a profile dict to a flat text string for indexing."""
        parts = [
            profile.get("name", ""),
            " ".join(profile.get("affiliations", [])),
            " ".join(profile.get("research_areas", [])),
            " ".join(p.get("title", "") for p in profile.get("publications", [])[:5]),
            profile.get("email", ""),
            profile.get("department", ""),
            profile.get("location", ""),
        ]
        return " ".join(filter(None, parts))

    def _rebuild_bm25(self):
        try:
            from rank_bm25 import BM25Okapi
            corpus = [self._profile_to_text(p).lower().split() for p in self.indexed_profiles]
            self.bm25 = BM25Okapi(corpus)
        except Exception as e:
            logger.warning(f"BM25 rebuild error: {e}")

    def _build_faiss_index(self, profiles: List[Dict]):
        if not self._model_loaded or not self.embeddings_model:
            return
        try:
            import faiss
            texts = [self._profile_to_text(p) for p in profiles]
            embeddings = self.embeddings_model.encode(texts, show_progress_bar=False)
            embeddings = np.array(embeddings, dtype=np.float32)
            faiss.normalize_L2(embeddings)
            dim = embeddings.shape[1]
            self.faiss_index = faiss.IndexFlatIP(dim)
            self.faiss_index.add(embeddings)
            self._faiss_embeddings = embeddings
            logger.info(f"FAISS index built with {len(profiles)} vectors")
        except Exception as e:
            logger.warning(f"FAISS index build error: {e}")

    # ─────────────────────────────────────────────
    # RANK: called at query time with freshly scraped profiles
    # ─────────────────────────────────────────────
    def rank(self, profiles: List[Dict], query: str) -> List[Dict]:
        if not profiles:
            return profiles
        if len(profiles) == 1:
            return profiles

        bm25_scores = self._bm25_score(profiles, query)
        semantic_scores = self._semantic_score(profiles, query)
        fused = self._reciprocal_rank_fusion(bm25_scores, semantic_scores)

        ranked = sorted(
            zip(profiles, fused),
            key=lambda x: x[1],
            reverse=True
        )
        result = []
        for prof, score in ranked:
            quality_bonus = self._quality_bonus(prof)
            prof["relevance_score"] = round(float(score + quality_bonus), 4)
            result.append(prof)
        result.sort(key=lambda prof: prof.get("relevance_score", 0), reverse=True)
        return result

    def _quality_bonus(self, profile: Dict) -> float:
        citations = max(int(profile.get("metrics", {}).get("citations", 0) or 0), 0)
        papers = max(int(profile.get("metrics", {}).get("paper_count", 0) or 0), 0)
        disambiguation = float(profile.get("disambiguation_score", 0) or 0)
        source_relevance = float(profile.get("source_relevance", 0) or 0)
        richness = sum(
            1 for value in [
                profile.get("university"),
                profile.get("department"),
                profile.get("location"),
                profile.get("email"),
                profile.get("phone"),
                profile.get("research_areas"),
                profile.get("publications"),
            ] if value
        )
        citation_bonus = min(log10(citations + 1) / 50, 0.12)
        paper_bonus = min(log10(papers + 1) / 80, 0.05)
        source_bonus = min(log10(source_relevance + 1) / 100, 0.08) if source_relevance > 0 else 0
        disambiguation_bonus = disambiguation / 100
        richness_bonus = min(richness * 0.005, 0.03)
        return citation_bonus + paper_bonus + source_bonus + disambiguation_bonus + richness_bonus

    def _bm25_score(self, profiles: List[Dict], query: str) -> List[float]:
        try:
            from rank_bm25 import BM25Okapi
            corpus = [self._profile_to_text(p).lower().split() for p in profiles]
            bm25 = BM25Okapi(corpus)
            scores = bm25.get_scores(query.lower().split())
            return scores.tolist()
        except Exception as e:
            logger.warning(f"BM25 scoring error: {e}")
            return [1.0] * len(profiles)

    def _semantic_score(self, profiles: List[Dict], query: str) -> List[float]:
        if not self._model_loaded or not self.embeddings_model:
            return [0.5] * len(profiles)
        try:
            import faiss
            texts = [self._profile_to_text(p) for p in profiles]
            corpus_emb = self.embeddings_model.encode(texts, show_progress_bar=False)
            query_emb = self.embeddings_model.encode([query], show_progress_bar=False)
            corpus_emb = np.array(corpus_emb, dtype=np.float32)
            query_emb = np.array(query_emb, dtype=np.float32)
            faiss.normalize_L2(corpus_emb)
            faiss.normalize_L2(query_emb)
            scores = (corpus_emb @ query_emb.T).flatten()
            return scores.tolist()
        except Exception as e:
            logger.warning(f"Semantic scoring error: {e}")
            return [0.5] * len(profiles)

    def _reciprocal_rank_fusion(
        self,
        bm25_scores: List[float],
        semantic_scores: List[float],
        k: int = 60,
        bm25_weight: float = 0.4,
        semantic_weight: float = 0.6
    ) -> List[float]:
        n = len(bm25_scores)
        bm25_ranks = np.argsort(np.argsort(-np.array(bm25_scores))) + 1
        sem_ranks = np.argsort(np.argsort(-np.array(semantic_scores))) + 1
        rrf_bm25 = [1.0 / (k + r) for r in bm25_ranks]
        rrf_sem = [1.0 / (k + r) for r in sem_ranks]
        fused = [
            bm25_weight * b + semantic_weight * s
            for b, s in zip(rrf_bm25, rrf_sem)
        ]
        return fused

    def index_size(self) -> int:
        return self._index_size

    def save_index(self):
        INDEX_PATH.parent.mkdir(exist_ok=True)
        with open(INDEX_PATH, "wb") as f:
            pickle.dump({"profiles": self.indexed_profiles}, f)
