"""
Pydantic models — request/response schemas for the API
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ── Request Models ─────────────────────────────────────────────────────────────

class SearchQuery(BaseModel):
    name: str = Field(..., min_length=2, description="Faculty member's name")
    affiliation: Optional[str] = Field(None, description="University or institution")
    research_area: Optional[str] = Field(None, description="Research domain / keyword")
    limit: int = Field(5, ge=1, le=20, description="Max results to return")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Andrew Ng",
                "affiliation": "Stanford",
                "research_area": "machine learning",
                "limit": 5
            }
        }


# ── Response Models ────────────────────────────────────────────────────────────

class Publication(BaseModel):
    title: str = ""
    year: str = ""
    citations: int = 0


class AcademicMetrics(BaseModel):
    citations: int = 0
    h_index: int = 0
    i10_index: int = 0
    paper_count: int = 0


class AcademicProfiles(BaseModel):
    google_scholar: Optional[str] = None
    orcid: Optional[str] = None
    openalex: Optional[str] = None
    semantic_scholar: Optional[str] = None


class FacultyProfile(BaseModel):
    name: str = ""
    university: str = ""
    department: str = ""
    affiliations: List[str] = []
    location: str = ""
    email: str = ""
    homepage: str = ""
    profile_image: str = ""
    research_areas: List[str] = []
    research_summary: str = ""
    publications: List[Publication] = []
    metrics: AcademicMetrics = AcademicMetrics()
    academic_profiles: Dict[str, str] = {}
    sources: List[str] = []
    disambiguation_score: float = 0.0
    relevance_score: float = 0.0


class SearchResponse(BaseModel):
    query: Dict[str, Any]
    count: int
    profiles: List[FacultyProfile]


class HealthResponse(BaseModel):
    status: str
    index_size: int
    cache_entries: int
    version: str = "1.0.0"
