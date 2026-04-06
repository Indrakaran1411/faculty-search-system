"""
Faculty Scraper Final — Uses multiple strategies to get complete profile:
1. OpenAlex + Semantic Scholar (reliable, no blocks)
2. ORCID (designation, department, location)
3. Direct Google Scholar profile scraping (bypasses login block)
4. Homepage scraping for phone/courses
"""

import ssl
import asyncio
import aiohttp
import logging
import re
import requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings()


class FacultyScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/json,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _connector(self):
        return aiohttp.TCPConnector(ssl=False)

    # ─────────────────────────────────────────────
    # MAIN
    # ─────────────────────────────────────────────
    async def fetch_all(self, name: str, affiliation: Optional[str] = None, research_area: Optional[str] = None) -> List[Dict]:
        tasks = [
            self._fetch_openalex(name, affiliation),
            self._fetch_semantic_scholar(name, affiliation),
            self._fetch_orcid(name, affiliation),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        combined = []
        for r in results:
            if isinstance(r, list):
                combined.extend(r)

        # Direct Scholar scrape in thread
        try:
            scholar = await asyncio.get_event_loop().run_in_executor(
                None, self._scrape_scholar_direct, name, affiliation
            )
            combined.extend(scholar)
        except Exception as e:
            logger.warning(f"Scholar scrape error: {e}")

        logger.info(f"Total raw profiles: {len(combined)}")
        return combined

    # ─────────────────────────────────────────────
    # DIRECT GOOGLE SCHOLAR SCRAPE
    # Scrapes scholar search page directly (no scholarly library)
    # ─────────────────────────────────────────────
    def _scrape_scholar_direct(self, name: str, affiliation: Optional[str]) -> List[Dict]:
        results = []
        try:
            query = name + (f" {affiliation}" if affiliation else "")
            url = f"https://scholar.google.com/citations?view_op=search_authors&mauthors={requests.utils.quote(query)}&hl=en"
            r = requests.get(url, headers=self.headers, timeout=10, verify=False)

            if r.status_code != 200 or "accounts.google" in r.url:
                logger.warning("Scholar blocked, trying scholarly library...")
                return self._try_scholarly(name, affiliation)

            soup = BeautifulSoup(r.text, "html.parser")
            cards = soup.find_all("div", class_="gsc_1usr")

            for card in cards[:5]:
                name_el = card.find("h3", class_="gs_ai_name")
                affil_el = card.find("div", class_="gs_ai_aff")
                email_el = card.find("div", class_="gs_ai_eml")
                interests_el = card.find_all("a", class_="gs_ai_one_int")
                img_el = card.find("img")
                link_el = name_el.find("a") if name_el else None

                author_name = name_el.get_text(strip=True) if name_el else ""
                affil_text = affil_el.get_text(strip=True) if affil_el else ""
                email_text = email_el.get_text(strip=True) if email_el else ""
                interests = [i.get_text(strip=True) for i in interests_el]
                img_url = img_el.get("src", "") if img_el else ""
                scholar_id = ""
                if link_el and "user=" in link_el.get("href", ""):
                    scholar_id = link_el["href"].split("user=")[1].split("&")[0]

                designation, department, university = self._parse_affiliation(affil_text)

                # Get full profile if we have scholar_id
                citations, h_index, i10_index, publications = 0, 0, 0, []
                if scholar_id:
                    citations, h_index, i10_index, publications = self._get_scholar_profile(scholar_id)

                results.append({
                    "source": "google_scholar",
                    "name": author_name,
                    "affiliations": [affil_text] if affil_text else [],
                    "designation": designation,
                    "department": department,
                    "university": university,
                    "email": email_text.replace("Verified email at ", "").strip(),
                    "phone": "",
                    "location": "",
                    "research_areas": interests,
                    "course_works": [],
                    "citation_count": citations,
                    "h_index": h_index,
                    "i10_index": i10_index,
                    "homepage": "",
                    "scholar_id": scholar_id,
                    "scholar_url": f"https://scholar.google.com/citations?user={scholar_id}" if scholar_id else "",
                    "profile_image": img_url,
                    "publications": publications,
                    "paper_count": len(publications),
                })
            return results
        except Exception as e:
            logger.warning(f"Scholar direct scrape error: {e}")
            return self._try_scholarly(name, affiliation)

    def _get_scholar_profile(self, scholar_id: str):
        """Get citations and publications from scholar profile page."""
        try:
            url = f"https://scholar.google.com/citations?user={scholar_id}&hl=en&sortby=pubdate"
            r = requests.get(url, headers=self.headers, timeout=10, verify=False)
            if r.status_code != 200:
                return 0, 0, 0, []
            soup = BeautifulSoup(r.text, "html.parser")

            # Metrics
            stats = soup.find_all("td", class_="gsc_rsb_std")
            citations = int(stats[0].get_text()) if len(stats) > 0 else 0
            h_index = int(stats[2].get_text()) if len(stats) > 2 else 0
            i10_index = int(stats[4].get_text()) if len(stats) > 4 else 0

            # Publications
            pub_rows = soup.find_all("tr", class_="gsc_a_tr")
            publications = []
            for row in pub_rows[:15]:
                title_el = row.find("a", class_="gsc_a_at")
                year_el = row.find("span", class_="gsc_a_h gsc_a_hc gs_ibl")
                cite_el = row.find("a", class_="gsc_a_ac gs_ibl")
                title = title_el.get_text(strip=True) if title_el else ""
                year = year_el.get_text(strip=True) if year_el else ""
                try:
                    cites = int(cite_el.get_text(strip=True)) if cite_el else 0
                except:
                    cites = 0
                if title:
                    publications.append({"title": title, "year": year, "citations": cites, "venue": ""})

            return citations, h_index, i10_index, publications
        except Exception as e:
            logger.warning(f"Scholar profile error: {e}")
            return 0, 0, 0, []

    def _try_scholarly(self, name: str, affiliation: Optional[str]) -> List[Dict]:
        """Fallback: use scholarly library."""
        try:
            from scholarly import scholarly as sc
            query = name + (f" {affiliation}" if affiliation else "")
            results = []
            for i, author in enumerate(sc.search_author(query)):
                if i >= 5:
                    break
                try:
                    filled = sc.fill(author, sections=["basics", "indices", "publications"])
                    pubs = filled.get("publications", [])
                    publications = [{"title": p.get("bib", {}).get("title", ""), "year": p.get("bib", {}).get("pub_year", ""), "citations": p.get("num_citations", 0), "venue": p.get("bib", {}).get("venue", "")} for p in pubs[:15]]
                    publications.sort(key=lambda x: x.get("citations", 0), reverse=True)
                    affil_raw = filled.get("affiliation", "")
                    designation, department, university = self._parse_affiliation(affil_raw)
                    homepage = filled.get("homepage", "")
                    phone, location, courses = self._scrape_homepage(homepage) if homepage else ("", "", [])
                    results.append({
                        "source": "google_scholar",
                        "name": filled.get("name", ""),
                        "affiliations": [affil_raw] if affil_raw else [],
                        "designation": designation,
                        "department": department,
                        "university": university,
                        "email": filled.get("email", ""),
                        "phone": phone,
                        "location": location,
                        "research_areas": filled.get("interests", []),
                        "course_works": courses,
                        "citation_count": filled.get("citedby", 0),
                        "h_index": filled.get("hindex", 0),
                        "i10_index": filled.get("i10index", 0),
                        "homepage": homepage,
                        "scholar_id": filled.get("scholar_id", ""),
                        "scholar_url": f"https://scholar.google.com/citations?user={filled.get('scholar_id', '')}",
                        "profile_image": filled.get("url_picture", ""),
                        "publications": publications,
                        "paper_count": len(pubs),
                        "course_works": courses,
                    })
                except Exception as e:
                    logger.warning(f"Scholarly fill error: {e}")
            return results
        except Exception as e:
            logger.warning(f"Scholarly error: {e}")
            return []

    # ─────────────────────────────────────────────
    # SCRAPE HOMEPAGE for phone/courses/location
    # ─────────────────────────────────────────────
    def _scrape_homepage(self, url: str):
        phone, location, courses = "", "", []
        try:
            r = requests.get(url, headers=self.headers, timeout=8, verify=False)
            if r.status_code != 200:
                return phone, location, courses
            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text(separator=" ")

            # Phone
            phone_patterns = [
                r'(?:phone|tel|mobile|ph)[.\s:]*([+\d\s\-().]{7,20})',
                r'\+\d[\d\s\-().]{8,18}',
                r'\(\d{3}\)\s*\d{3}[-.\s]\d{4}',
            ]
            for pat in phone_patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    phone = m.group(0).strip()[:25]
                    break

            # Location/Office
            loc_patterns = [
                r'(?:office|room|building|location)[:\s]+([A-Za-z0-9\s,.\-]{5,60})',
                r'(?:address)[:\s]+([A-Za-z0-9\s,.\-]{5,80})',
            ]
            for pat in loc_patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    location = m.group(1).strip()[:60]
                    break

            # Courses
            course_patterns = [
                r'(?:CS|ECE|EE|ME|AI|ML|CSE|IT)\s*\d{2,4}[:\s\-]+([A-Za-z\s&]+)',
                r'(?:teach|course|class)[es]?[:\s]+([A-Za-z0-9\s,&\-]+?)(?:\.|,|\n)',
            ]
            for pat in course_patterns:
                for m in re.finditer(pat, text, re.IGNORECASE):
                    c = m.group(1).strip()
                    if 3 < len(c) < 60:
                        courses.append(c)
                if courses:
                    break
        except Exception as e:
            logger.warning(f"Homepage scrape error: {e}")
        return phone, location[:60], courses[:5]

    # ─────────────────────────────────────────────
    # OPENALEX
    # ─────────────────────────────────────────────
    async def _fetch_openalex(self, name: str, affiliation: Optional[str]) -> List[Dict]:
        params = {"search": name, "per-page": 8, "mailto": "faculty-search@local.dev"}
        try:
            async with aiohttp.ClientSession(connector=self._connector()) as session:
                async with session.get("https://api.openalex.org/authors", params=params,
                    headers=self.headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    results = []
                    for a in data.get("results", []):
                        inst = a.get("last_known_institution") or {}
                        concepts = a.get("x_concepts", [])
                        research_areas = [c.get("display_name", "") for c in concepts[:6] if c.get("level", 0) <= 2]
                        uni = inst.get("display_name", "")
                        country = inst.get("country_code", "")

                        # Fetch detailed works for publications
                        author_id = a.get("id", "").split("/")[-1]
                        publications = await self._fetch_openalex_works(author_id, session)

                        results.append({
                            "source": "openalex",
                            "name": a.get("display_name", ""),
                            "affiliations": [uni] if uni else [],
                            "university": uni,
                            "designation": "",
                            "department": "",
                            "location": country,
                            "email": "",
                            "phone": "",
                            "course_works": [],
                            "paper_count": a.get("works_count", 0),
                            "citation_count": a.get("cited_by_count", 0),
                            "h_index": a.get("summary_stats", {}).get("h_index", 0),
                            "i10_index": a.get("summary_stats", {}).get("i10_index", 0),
                            "openalex_url": a.get("id", ""),
                            "orcid_url": a.get("orcid", ""),
                            "research_areas": research_areas,
                            "homepage": "",
                            "publications": publications,
                            "profile_image": "",
                        })
                    return results
        except Exception as e:
            logger.warning(f"OpenAlex error: {e}")
            return []

    async def _fetch_openalex_works(self, author_id: str, session) -> List[Dict]:
        """Fetch top publications for an OpenAlex author."""
        try:
            url = f"https://api.openalex.org/works"
            params = {
                "filter": f"author.id:{author_id}",
                "sort": "cited_by_count:desc",
                "per-page": 10
            }
            async with session.get(url, params=params, headers=self.headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                works = []
                for w in data.get("results", []):
                    title = w.get("title", "")
                    year = w.get("publication_year", "")
                    citations = w.get("cited_by_count", 0)
                    venue = w.get("primary_location", {}).get("source", {})
                    venue_name = venue.get("display_name", "") if venue else ""
                    if title:
                        works.append({"title": title, "year": str(year) if year else "", "citations": citations, "venue": venue_name})
                return works
        except Exception:
            return []

    # ─────────────────────────────────────────────
    # SEMANTIC SCHOLAR
    # ─────────────────────────────────────────────
    async def _fetch_semantic_scholar(self, name: str, affiliation: Optional[str]) -> List[Dict]:
        query = name + (f" {affiliation}" if affiliation else "")
        params = {
            "query": query, "limit": 8,
            "fields": "name,affiliations,paperCount,citationCount,hIndex,homepage,papers.title,papers.year,papers.citationCount,papers.venue"
        }
        try:
            async with aiohttp.ClientSession(connector=self._connector()) as session:
                async with session.get("https://api.semanticscholar.org/graph/v1/author/search",
                    params=params, headers=self.headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    results = []
                    for a in data.get("data", []):
                        papers = a.get("papers", [])
                        affils = [af.get("name", "") for af in a.get("affiliations", [])]
                        designation, department, university = self._parse_affiliation(" | ".join(affils))
                        results.append({
                            "source": "semantic_scholar",
                            "name": a.get("name", ""),
                            "affiliations": affils,
                            "designation": designation,
                            "department": department,
                            "university": university,
                            "email": "", "phone": "", "location": "", "course_works": [],
                            "paper_count": a.get("paperCount", 0),
                            "citation_count": a.get("citationCount", 0),
                            "h_index": a.get("hIndex", 0),
                            "homepage": a.get("homepage", ""),
                            "semantic_scholar_url": f"https://www.semanticscholar.org/author/{a.get('authorId', '')}",
                            "research_areas": [],
                            "profile_image": "",
                            "publications": [
                                {"title": p.get("title", ""), "year": p.get("year"), "citations": p.get("citationCount", 0), "venue": p.get("venue", "") or ""}
                                for p in sorted(papers, key=lambda x: x.get("citationCount", 0), reverse=True)[:10]
                            ]
                        })
                    return results
        except Exception as e:
            logger.warning(f"Semantic Scholar error: {e}")
            return []

    # ─────────────────────────────────────────────
    # ORCID
    # ─────────────────────────────────────────────
    async def _fetch_orcid(self, name: str, affiliation: Optional[str]) -> List[Dict]:
        parts = name.strip().split()
        query = f"family-name:{parts[-1]} AND given-names:{parts[0]}" if len(parts) >= 2 else name
        if affiliation:
            query += f" AND affiliation-org-name:{affiliation}"
        try:
            async with aiohttp.ClientSession(connector=self._connector()) as session:
                async with session.get("https://pub.orcid.org/v3.0/search/",
                    params={"q": query, "rows": 5},
                    headers={**self.headers, "Accept": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    profiles = []
                    for item in (data.get("result", []) or []):
                        orcid_id = item.get("orcid-identifier", {}).get("path", "")
                        if orcid_id:
                            detail = await self._fetch_orcid_detail(orcid_id, session)
                            if detail:
                                profiles.append(detail)
                    return profiles
        except Exception as e:
            logger.warning(f"ORCID error: {e}")
            return []

    async def _fetch_orcid_detail(self, orcid_id: str, session) -> Optional[Dict]:
        try:
            async with session.get(
                f"https://pub.orcid.org/v3.0/{orcid_id}/record",
                headers={**self.headers, "Accept": "application/json"},
                timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                person = data.get("person", {})
                name_data = person.get("name", {})
                emails = person.get("emails", {}).get("email", [])
                email = emails[0].get("email", "") if emails else ""
                activities = data.get("activities-summary", {})
                employments = activities.get("employments", {}).get("affiliation-group", [])
                affiliations, designation, department, university, location = [], "", "", "", ""
                for emp in employments[:3]:
                    for s in emp.get("summaries", []):
                        es = s.get("employment-summary", {})
                        org = es.get("organization", {})
                        role = es.get("role-title", "")
                        dept = es.get("department-name", "")
                        org_name = org.get("name", "")
                        addr = org.get("address", {})
                        city = addr.get("city", "")
                        country = addr.get("country", "")
                        if org_name:
                            affiliations.append(org_name)
                            if not university: university = org_name
                        if role and not designation: designation = role
                        if dept and not department: department = dept
                        if (city or country) and not location:
                            location = f"{city}, {country}".strip(", ")
                works = activities.get("works", {}).get("group", [])
                publications = []
                for w in works[:15]:
                    ws = w.get("work-summary", [{}])[0]
                    title = ws.get("title", {}).get("title", {}).get("value", "")
                    year = ws.get("publication-date", {}).get("year", {}).get("value", "")
                    if title:
                        publications.append({"title": title, "year": year, "citations": 0, "venue": ""})
                given = name_data.get("given-names", {}).get("value", "")
                family = name_data.get("family-name", {}).get("value", "")
                return {
                    "source": "orcid",
                    "name": f"{given} {family}".strip(),
                    "orcid_id": orcid_id,
                    "orcid_url": f"https://orcid.org/{orcid_id}",
                    "email": email, "phone": "",
                    "affiliations": affiliations,
                    "designation": designation, "department": department,
                    "university": university, "location": location,
                    "course_works": [], "publications": publications,
                    "paper_count": len(works), "citation_count": 0,
                    "h_index": 0, "homepage": "", "research_areas": [], "profile_image": "",
                }
        except Exception as e:
            logger.warning(f"ORCID detail error: {e}")
            return None

    async def fetch_by_scholar_id(self, scholar_id: str) -> Optional[Dict]:
        try:
            loop = asyncio.get_event_loop()
            citations, h_index, i10_index, publications = await loop.run_in_executor(
                None, self._get_scholar_profile, scholar_id
            )
            return {
                "source": "google_scholar",
                "name": "", "affiliations": [], "designation": "",
                "department": "", "university": "", "email": "", "phone": "",
                "location": "", "research_areas": [], "course_works": [],
                "citation_count": citations, "h_index": h_index, "i10_index": i10_index,
                "homepage": "", "scholar_id": scholar_id,
                "scholar_url": f"https://scholar.google.com/citations?user={scholar_id}",
                "profile_image": "", "publications": publications, "paper_count": len(publications),
            }
        except Exception as e:
            logger.error(f"Scholar ID error: {e}")
            return None

    def _parse_affiliation(self, text: str):
        designation_kws = ["Professor", "Associate Professor", "Assistant Professor",
                           "Lecturer", "Senior Lecturer", "Reader", "Dean", "Director",
                           "Researcher", "Scientist", "Fellow", "Instructor", "Chair",
                           "Head", "Principal", "PostDoc", "Adjunct", "Emeritus"]
        dept_kws = ["Department", "Dept", "School of", "Faculty of", "Division", "College of", "Institute of"]
        uni_kws = ["University", "Institute", "College", "Academy", "IIT", "NIT", "BITS", "MIT", "IIM", "School"]
        designation, department, university = "", "", ""
        for kw in designation_kws:
            if kw.lower() in text.lower():
                designation = kw
                break
        parts = [p.strip() for p in re.split(r"[,|;]", text) if p.strip()]
        for p in parts:
            if not department and any(kw.lower() in p.lower() for kw in dept_kws):
                department = p
            if not university and any(kw.lower() in p.lower() for kw in uni_kws):
                university = p
        if not university and parts:
            university = parts[-1]
        return designation, department, university
