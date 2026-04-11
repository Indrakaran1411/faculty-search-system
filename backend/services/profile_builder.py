"""
Profile Builder v3 — Returns all required fields cleanly
"""

import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def _clean_email(email: str) -> str:
    if not email:
        return ""
    email = email.strip().lower()
    return email if re.match(r"[^@]+@[^@]+\.[^@]+", email) else ""


def _clean_url(url: str) -> str:
    if not url:
        return ""
    return url if url.startswith("http") else "https://" + url


def _best(values: list, default=""):
    return next((v for v in values if v), default)


class ProfileBuilder:
    def build(self, raw: Dict) -> Dict:
        name        = raw.get("name", "").strip()
        affiliations = [a.strip() for a in raw.get("affiliations", []) if a and a.strip()]
        research_areas = [r.strip() for r in raw.get("research_areas", []) if r and r.strip()]
        publications   = raw.get("publications", [])
        course_works   = raw.get("course_works", [])

        designation = raw.get("designation", "")
        university  = raw.get("university", "") or (affiliations[0] if affiliations else "")
        department  = raw.get("department", "")
        location    = raw.get("location", "") or raw.get("institution_country", "")
        email       = _clean_email(raw.get("email", ""))
        phone       = raw.get("phone", "")
        homepage    = _clean_url(raw.get("homepage", ""))

        if not location and affiliations:
            location = affiliations[0]
        if not university and location and location not in affiliations:
            affiliations.insert(0, location)

        academic_profiles = {}
        if raw.get("scholar_url"):
            academic_profiles["google_scholar"] = raw["scholar_url"]
        if raw.get("orcid_url"):
            academic_profiles["orcid"] = raw["orcid_url"]
        if raw.get("openalex_url"):
            academic_profiles["openalex"] = raw["openalex_url"]
        if raw.get("semantic_scholar_url"):
            academic_profiles["semantic_scholar"] = raw["semantic_scholar_url"]

        top_pubs = [
            {
                "title":     p.get("title", ""),
                "year":      str(p.get("year", "")) if p.get("year") else "",
                "citations": int(p.get("citations", 0) or 0),
                "venue":     p.get("venue", "")
            }
            for p in publications[:15]
        ]

        metrics = {
            "citations":   int(raw.get("citation_count", 0) or 0),
            "h_index":     int(raw.get("h_index", 0) or 0),
            "i10_index":   int(raw.get("i10_index", 0) or 0),
            "paper_count": int(raw.get("paper_count", 0) or 0),
        }

        return {
            "name":            name,
            "designation":     designation,
            "university":      university,
            "department":      department,
            "location":        location,
            "email":           email,
            "phone":           phone,
            "homepage":        homepage,
            "profile_image":   raw.get("profile_image", ""),
            "research_areas":  research_areas,
            "course_works":    course_works,
            "publications":    top_pubs,
            "metrics":         metrics,
            "academic_profiles": academic_profiles,
            "affiliations":    affiliations,
            "sources":         raw.get("sources", [raw.get("source", "")]),
            "disambiguation_score": raw.get("disambiguation_score", 0),
            "relevance_score":      raw.get("relevance_score", 0),
            "source_relevance":     raw.get("source_relevance", 0),
        }
