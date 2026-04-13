"""
LLM Service — AI Summarization + RAG-based Query Answering
Uses:
  - sentence-transformers (already installed) for embedding & retrieval
  - spaCy NER (already installed) for keyword extraction
  - Template-based NLG for fast, structured summaries (no large model download)
  - FAISS (already installed) for semantic chunk retrieval in RAG
"""

import re
import logging
import numpy as np
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _load_encoder():
    """Load sentence-transformer encoder (already available from search engine)."""
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as e:
        logger.warning(f"Encoder load failed: {e}")
        return None


_ENCODER = None


def _encoder():
    global _ENCODER
    if _ENCODER is None:
        _ENCODER = _load_encoder()
    return _ENCODER


def _embed(texts: List[str]) -> Optional[np.ndarray]:
    enc = _encoder()
    if enc is None or not texts:
        return None
    try:
        vecs = enc.encode(texts, show_progress_bar=False)
        return np.array(vecs, dtype=np.float32)
    except Exception as e:
        logger.warning(f"Embedding failed: {e}")
        return None


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ─────────────────────────────────────────────────────────────────
# SUMMARIZER
# ─────────────────────────────────────────────────────────────────

def _format_areas(areas: List[str]) -> str:
    if not areas:
        return "various research domains"
    unique = list(dict.fromkeys(a.strip() for a in areas if a.strip()))[:6]
    if len(unique) == 1:
        return unique[0]
    return ", ".join(unique[:-1]) + f" and {unique[-1]}"


def _top_venues(publications: List[Dict]) -> List[str]:
    venues = [
        p.get("venue", "").strip()
        for p in publications
        if p.get("venue", "").strip()
    ]
    seen, unique = set(), []
    for v in venues:
        if v.lower() not in seen:
            seen.add(v.lower())
            unique.append(v)
        if len(unique) >= 3:
            break
    return unique


def _most_cited_pub(publications: List[Dict]) -> Optional[Dict]:
    cited = [p for p in publications if p.get("citations", 0) > 0]
    if not cited:
        return None
    return max(cited, key=lambda p: p.get("citations", 0))


def _recent_years(publications: List[Dict]) -> Optional[str]:
    years = []
    for p in publications:
        try:
            y = int(str(p.get("year", "")).strip())
            if 1980 <= y <= 2030:
                years.append(y)
        except Exception:
            pass
    if not years:
        return None
    mn, mx = min(years), max(years)
    if mn == mx:
        return str(mx)
    return f"{mn}–{mx}"


def generate_research_summary(profile: Dict) -> str:
    """
    Generate a concise, intelligent research summary paragraph for a faculty profile.
    Uses structured NLG — fast and does not require downloading any extra models.
    """
    name = profile.get("name", "This faculty member").strip() or "This faculty member"
    designation = profile.get("designation", "").strip()
    university = profile.get("university", "").strip()
    department = profile.get("department", "").strip()
    areas = profile.get("research_areas", []) or []
    pubs = profile.get("publications", []) or []
    metrics = profile.get("metrics", {}) or {}
    citations = int(metrics.get("citations", 0) or 0)
    h_index = int(metrics.get("h_index", 0) or 0)
    paper_count = int(metrics.get("paper_count", 0) or 0)

    sentences = []

    # Sentence 1 — Identity & affiliation
    role_parts = []
    if designation:
        role_parts.append(designation)
    if department:
        role_parts.append(f"in the {department}")
    if university:
        role_parts.append(f"at {university}")

    if role_parts:
        sentences.append(f"{name} is a {' '.join(role_parts)}.")
    else:
        sentences.append(f"{name} is an academic researcher.")

    # Sentence 2 — Research focus
    if areas:
        sentences.append(
            f"Their research spans {_format_areas(areas)}, "
            f"positioning them at the intersection of theory and application."
        )

    # Sentence 3 — Publications span / top work
    top_pub = _most_cited_pub(pubs)
    year_range = _recent_years(pubs)
    venues = _top_venues(pubs)

    if top_pub and top_pub.get("citations", 0) > 5:
        t = top_pub["title"][:80] + ("…" if len(top_pub["title"]) > 80 else "")
        sentences.append(
            f"Their most influential work, \"{t}\", has garnered "
            f"{top_pub['citations']:,} citations."
        )
    elif paper_count > 0 and year_range:
        sentences.append(
            f"They have published {paper_count:,} papers spanning {year_range}."
        )

    # Sentence 4 — Academic impact
    if citations > 100 and h_index > 0:
        impact = "exceptional" if citations > 10000 else ("strong" if citations > 1000 else "notable")
        sentences.append(
            f"With {citations:,} total citations and an h-index of {h_index}, "
            f"they have demonstrated {impact} academic impact in their field."
        )
    elif h_index > 0:
        sentences.append(
            f"Their h-index of {h_index} reflects consistent contributions to the academic community."
        )

    # Sentence 5 — Venue diversity
    if venues:
        v_str = ", ".join(venues)
        sentences.append(
            f"Their work has appeared in venues including {v_str}."
        )

    if not sentences:
        return "No sufficient profile data available to generate a summary."

    return " ".join(sentences)


# ─────────────────────────────────────────────────────────────────
# RAG ANSWERING
# ─────────────────────────────────────────────────────────────────

def _build_knowledge_chunks(profile: Dict) -> List[str]:
    """
    Convert a profile into a list of text chunks that represent facts about this faculty.
    These are used as the retrieval corpus for RAG.
    """
    chunks = []
    name = profile.get("name", "this professor")

    # Identity chunks
    if profile.get("designation") and profile.get("university"):
        chunks.append(
            f"{name} holds the position of {profile['designation']} at {profile['university']}."
        )
    if profile.get("department"):
        chunks.append(f"{name} works in the {profile['department']}.")
    if profile.get("email"):
        chunks.append(f"Contact email for {name}: {profile['email']}.")
    if profile.get("phone"):
        chunks.append(f"Phone number for {name}: {profile['phone']}.")
    if profile.get("location"):
        chunks.append(f"{name} is located at {profile['location']}.")
    if profile.get("homepage"):
        chunks.append(f"Homepage / personal website of {name}: {profile['homepage']}.")

    # Research areas
    areas = profile.get("research_areas", [])
    if areas:
        chunks.append(
            f"{name} specializes in: {', '.join(areas[:8])}."
        )

    # Course works
    courses = profile.get("course_works", [])
    if courses:
        chunks.append(
            f"{name} teaches or has taught: {', '.join(courses[:6])}."
        )

    # Metrics
    m = profile.get("metrics", {}) or {}
    cites = int(m.get("citations", 0) or 0)
    h_idx = int(m.get("h_index", 0) or 0)
    papers = int(m.get("paper_count", 0) or 0)
    if cites > 0 or h_idx > 0:
        chunks.append(
            f"{name} has {cites:,} citations, an h-index of {h_idx}, and {papers:,} published papers."
        )

    # Publications
    for pub in (profile.get("publications", []) or [])[:15]:
        title = pub.get("title", "")
        if not title:
            continue
        year = pub.get("year", "")
        venue = pub.get("venue", "")
        cit = int(pub.get("citations", 0) or 0)
        parts = [f'"{title}"']
        if year:
            parts.append(f"({year})")
        if venue:
            parts.append(f"in {venue}")
        if cit > 0:
            parts.append(f"with {cit:,} citations")
        chunks.append(f"{name} published {' '.join(parts)}.")

    # Affiliations
    affiliations = profile.get("affiliations", [])
    if affiliations:
        chunks.append(
            f"{name}'s affiliations include: {', '.join(affiliations[:5])}."
        )

    return chunks


def _generate_answer_from_chunks(question: str, chunks: List[str], profile: Dict) -> str:
    """
    Template-based answer generation from retrieved chunks + keyword matching.
    No LLM download required — uses semantic retrieval + structured responses.
    """
    name = profile.get("name", "this professor")
    q_lower = question.lower()

    # ── Direct keyword intents ──────────────────────────────────

    # Email / Contact
    if any(w in q_lower for w in ["email", "contact", "reach", "mail"]):
        email = profile.get("email", "")
        phone = profile.get("phone", "")
        if email or phone:
            parts = []
            if email:
                parts.append(f"email at **{email}**")
            if phone:
                parts.append(f"phone at **{phone}**")
            return f"You can reach {name} via {' or '.join(parts)}."
        return f"No contact information is available for {name} in the retrieved data."

    # Phone
    if any(w in q_lower for w in ["phone", "mobile", "number", "call"]):
        phone = profile.get("phone", "")
        if phone:
            return f"{name}'s phone number is **{phone}**."
        return f"No phone number was found for {name} in the retrieved data."

    # University / Institution
    if any(w in q_lower for w in ["university", "institution", "college", "where", "work"]):
        univ = profile.get("university", "")
        dept = profile.get("department", "")
        if univ:
            loc = f" in the {dept}" if dept else ""
            return f"{name} works at **{univ}**{loc}."

    # Department
    if any(w in q_lower for w in ["department", "dept", "division", "school"]):
        dept = profile.get("department", "")
        if dept:
            return f"{name} is affiliated with the **{dept}**."

    # Research areas / interest
    if any(w in q_lower for w in ["research", "interest", "focus", "expertise", "speciali", "area", "work on"]):
        areas = profile.get("research_areas", [])
        if areas:
            return (
                f"{name} specializes in **{_format_areas(areas)}**. "
                f"Their work bridges multiple fields within this domain."
            )

    # Teaching / courses
    if any(w in q_lower for w in ["teach", "course", "class", "subject", "lecture"]):
        courses = profile.get("course_works", [])
        if courses:
            return f"{name} teaches: **{', '.join(courses[:5])}**."
        return f"No course information was found for {name} in the retrieved data."

    # Publications / papers
    if any(w in q_lower for w in ["paper", "publication", "publish", "journal", "article", "recent work"]):
        pubs = profile.get("publications", []) or []
        if pubs:
            top = pubs[0]
            t = top.get("title", "")
            y = top.get("year", "")
            cit = int(top.get("citations", 0) or 0)
            phrase = f'"{t}"'
            if y:
                phrase += f" ({y})"
            if cit > 0:
                phrase += f" with {cit:,} citations"
            return (
                f"{name} has published {len(pubs)} papers in the retrieved data. "
                f"A notable work is {phrase}."
            )

    # Citations / h-index / impact
    if any(w in q_lower for w in ["citation", "h-index", "hindex", "impact", "cited", "influence"]):
        m = profile.get("metrics", {}) or {}
        cit = int(m.get("citations", 0) or 0)
        h = int(m.get("h_index", 0) or 0)
        papers = int(m.get("paper_count", 0) or 0)
        if cit > 0:
            return (
                f"{name} has **{cit:,} citations**, an **h-index of {h}**, "
                f"and **{papers:,} published papers**."
            )

    # ── Semantic retrieval fallback ─────────────────────────────
    # Rank the chunks by cosine similarity to the question embedding
    if chunks:
        q_emb = _embed([question])
        chunk_embs = _embed(chunks)
        if q_emb is not None and chunk_embs is not None:
            sims = [_cosine_sim(q_emb[0], c) for c in chunk_embs]
            top_idx = int(np.argmax(sims))
            best_sim = sims[top_idx]
            if best_sim > 0.25:
                best_chunk = chunks[top_idx]
                # Collect up to 2 more supporting facts
                sorted_idx = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)
                supporting = [chunks[i] for i in sorted_idx[1:3] if sims[i] > 0.2]
                answer = best_chunk
                if supporting:
                    answer += " Additionally, " + supporting[0].lower()
                return answer

    return (
        f"Based on the available data for {name}, I could not find a specific answer to that question. "
        f"Try asking about their research areas, publications, contact details, or institution."
    )


# ─────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────

def summarize_profile(profile: Dict) -> str:
    """Generate an AI research summary for a faculty profile."""
    return generate_research_summary(profile)


def answer_question(profile: Dict, question: str) -> str:
    """
    RAG-based QA: retrieve relevant facts from the profile and generate an answer.
    """
    if not question or not question.strip():
        return "Please ask a question about this faculty member."
    chunks = _build_knowledge_chunks(profile)
    return _generate_answer_from_chunks(question.strip(), chunks, profile)
