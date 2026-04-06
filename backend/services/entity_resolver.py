"""
Entity Resolver
- Deduplicates faculty profiles from multiple sources
- Handles name ambiguity using contextual signals
- Merges data from multiple sources into unified entities
"""

import re
import logging
from typing import List, Dict, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def _normalize_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def _name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_name(a), _normalize_name(b)).ratio()


def _affiliation_overlap(a: List[str], b: List[str]) -> float:
    if not a or not b:
        return 0.0
    a_words = set(" ".join(a).lower().split())
    b_words = set(" ".join(b).lower().split())
    stop = {"university", "of", "the", "institute", "department", "college", "school", "and"}
    a_words -= stop
    b_words -= stop
    if not a_words or not b_words:
        return 0.0
    overlap = len(a_words & b_words) / max(len(a_words), len(b_words))
    return overlap


def _publication_overlap(a: List[Dict], b: List[Dict]) -> float:
    if not a or not b:
        return 0.0
    titles_a = {p.get("title", "").lower()[:60] for p in a if p.get("title")}
    titles_b = {p.get("title", "").lower()[:60] for p in b if p.get("title")}
    if not titles_a or not titles_b:
        return 0.0
    overlap = len(titles_a & titles_b) / max(len(titles_a), len(titles_b))
    return overlap


class EntityResolver:
    def __init__(self, name_threshold=0.82, merge_threshold=0.55):
        self.name_threshold = name_threshold
        self.merge_threshold = merge_threshold

    def resolve(
        self,
        profiles: List[Dict],
        query_name: str,
        query_affiliation: Optional[str] = None
    ) -> List[Dict]:
        """
        1. Filter out profiles whose name doesn't match the query
        2. Cluster profiles that refer to the same person
        3. Merge each cluster into one unified profile
        4. Score and sort by confidence
        """
        if not profiles:
            return []

        # Step 1: Filter by name similarity
        relevant = [
            p for p in profiles
            if _name_similarity(p.get("name", ""), query_name) >= self.name_threshold
        ]
        if not relevant:
            # Relax threshold if nothing matched
            relevant = [
                p for p in profiles
                if _name_similarity(p.get("name", ""), query_name) >= 0.5
            ]
        if not relevant:
            relevant = profiles  # fallback: return all

        # Step 2: Cluster
        clusters = self._cluster(relevant)

        # Step 3: Merge each cluster
        merged = [self._merge_cluster(cluster) for cluster in clusters]

        # Step 4: Score by relevance to query affiliation
        if query_affiliation:
            for p in merged:
                aff_score = _affiliation_overlap(p.get("affiliations", []), [query_affiliation])
                p["disambiguation_score"] = round(
                    _name_similarity(p.get("name", ""), query_name) * 0.5 + aff_score * 0.5, 3
                )
            merged.sort(key=lambda x: x.get("disambiguation_score", 0), reverse=True)
        else:
            for p in merged:
                p["disambiguation_score"] = round(
                    _name_similarity(p.get("name", ""), query_name), 3
                )
            merged.sort(key=lambda x: (x.get("citation_count", 0), x.get("paper_count", 0)), reverse=True)

        logger.info(f"Resolved {len(profiles)} raw profiles → {len(merged)} unique entities")
        return merged

    def _cluster(self, profiles: List[Dict]) -> List[List[Dict]]:
        """Group profiles that likely refer to the same person."""
        clusters = []
        assigned = [False] * len(profiles)

        for i, p in enumerate(profiles):
            if assigned[i]:
                continue
            cluster = [p]
            assigned[i] = True
            for j, q in enumerate(profiles):
                if i == j or assigned[j]:
                    continue
                if self._are_same_person(p, q):
                    cluster.append(q)
                    assigned[j] = True
            clusters.append(cluster)

        return clusters

    def _are_same_person(self, a: Dict, b: Dict) -> bool:
        name_sim = _name_similarity(a.get("name", ""), b.get("name", ""))
        if name_sim < self.name_threshold:
            return False
        aff_sim = _affiliation_overlap(a.get("affiliations", []), b.get("affiliations", []))
        pub_sim = _publication_overlap(a.get("publications", []), b.get("publications", []))
        score = name_sim * 0.4 + aff_sim * 0.35 + pub_sim * 0.25
        return score >= self.merge_threshold

    def _merge_cluster(self, cluster: List[Dict]) -> Dict:
        """Merge multiple source profiles into one unified profile."""
        if len(cluster) == 1:
            return cluster[0]

        merged = {}
        # Priority: google_scholar > semantic_scholar > openalex > orcid
        source_priority = ["google_scholar", "semantic_scholar", "openalex", "orcid"]

        def best_value(key: str, default=None):
            for src in source_priority:
                for p in cluster:
                    if p.get("source") == src and p.get(key):
                        return p[key]
            for p in cluster:
                if p.get(key):
                    return p[key]
            return default

        merged["name"] = best_value("name", "")
        merged["affiliations"] = list(set(
            aff for p in cluster for aff in p.get("affiliations", []) if aff
        ))
        merged["email"] = best_value("email", "")
        merged["homepage"] = best_value("homepage", "")
        merged["profile_image"] = best_value("profile_image", "")
        merged["research_areas"] = list(set(
            ra for p in cluster for ra in p.get("research_areas", []) if ra
        ))
        merged["citation_count"] = max((p.get("citation_count", 0) for p in cluster), default=0)
        merged["h_index"] = max((p.get("h_index", 0) for p in cluster), default=0)
        merged["i10_index"] = max((p.get("i10_index", 0) for p in cluster), default=0)
        merged["paper_count"] = max((p.get("paper_count", 0) for p in cluster), default=0)
        merged["scholar_url"] = best_value("scholar_url", "")
        merged["scholar_id"] = best_value("scholar_id", "")
        merged["orcid_url"] = best_value("orcid_url", "")
        merged["orcid_id"] = best_value("orcid_id", "")
        merged["openalex_url"] = best_value("openalex_url", "")
        merged["semantic_scholar_url"] = best_value("semantic_scholar_url", "")

        # Merge publications, deduplicate by title similarity
        all_pubs = []
        seen_titles = set()
        for p in cluster:
            for pub in p.get("publications", []):
                title_key = pub.get("title", "").lower()[:50]
                if title_key and title_key not in seen_titles:
                    seen_titles.add(title_key)
                    all_pubs.append(pub)
        all_pubs.sort(key=lambda x: x.get("citations", 0), reverse=True)
        merged["publications"] = all_pubs[:20]
        merged["sources"] = list(set(p.get("source", "") for p in cluster))

        return merged
