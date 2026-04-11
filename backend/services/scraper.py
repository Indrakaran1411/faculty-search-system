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
from urllib.parse import urlparse, parse_qs, unquote
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
        self.request_timeout = 5
        self.search_result_limit = 6

    def _connector(self):
        return aiohttp.TCPConnector(ssl=False)

    def _normalize_country(self, country_code: str) -> str:
        countries = {
            "CA": "Canada",
            "US": "United States",
            "GB": "United Kingdom",
            "FR": "France",
            "DE": "Germany",
            "IL": "Israel",
            "KR": "South Korea",
            "SG": "Singapore",
            "PL": "Poland",
            "AT": "Austria",
            "GH": "Ghana",
            "DZ": "Algeria",
            "ID": "Indonesia",
            "CN": "China",
            "CO": "Colombia",
        }
        return countries.get((country_code or "").upper(), country_code or "")

    def _extract_openalex_affiliations(self, author: Dict):
        raw_affiliations = author.get("affiliations", []) or []
        last_known = author.get("last_known_institutions", []) or []
        institutions = []

        for item in raw_affiliations:
            institution = item.get("institution", {}) or {}
            years = item.get("years", []) or []
            name = institution.get("display_name", "")
            if name:
                institutions.append({
                    "name": name,
                    "country": self._normalize_country(institution.get("country_code", "")),
                    "type": institution.get("type", ""),
                    "recent_year": max(years) if years else 0,
                })

        if not institutions:
            for institution in last_known:
                name = institution.get("display_name", "")
                if name:
                    institutions.append({
                        "name": name,
                        "country": self._normalize_country(institution.get("country_code", "")),
                        "type": institution.get("type", ""),
                        "recent_year": 0,
                    })

        seen = set()
        deduped = []
        for institution in sorted(
            institutions,
            key=lambda item: (
                0 if item["type"] == "education" else 1,
                -item["recent_year"],
                item["name"],
            ),
        ):
            key = institution["name"].lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(institution)

        names = [item["name"] for item in deduped[:5]]
        primary = deduped[0] if deduped else {}
        location = ", ".join(filter(None, [primary.get("name", ""), primary.get("country", "")]))
        return names, primary.get("name", ""), location

    # ─────────────────────────────────────────────
    # MAIN
    # ─────────────────────────────────────────────
    async def fetch_all(self, name: str, affiliation: Optional[str] = None, research_area: Optional[str] = None) -> List[Dict]:
        tasks = [
            asyncio.create_task(self._fetch_openalex(name, affiliation)),
            asyncio.create_task(self._fetch_semantic_scholar(name, affiliation)),
            asyncio.create_task(self._fetch_orcid(name, affiliation)),
        ]
        done, pending = await asyncio.wait(tasks, timeout=self.request_timeout + 1)
        for pending_task in pending:
            pending_task.cancel()

        combined = []
        for task in done:
            try:
                result = task.result()
                if isinstance(result, list):
                    combined.extend(result)
            except Exception as e:
                logger.warning(f"Primary source task failed: {e}")

        # Only attempt Scholar as a last resort, and cap it tightly.
        if not combined:
            try:
                scholar = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, self._scrape_scholar_direct, name, affiliation
                    ),
                    timeout=4,
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
            r = requests.get(url, headers=self.headers, timeout=self.request_timeout, verify=False)

            if r.status_code != 200 or "accounts.google" in r.url:
                logger.warning("Scholar blocked, skipping Google Scholar source for this query.")
                return []

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
            return []

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

    def _page_text(self, soup: BeautifulSoup) -> str:
        return re.sub(r"\s+", " ", soup.get_text(separator=" ", strip=True))

    def _extract_email(self, text: str) -> str:
        matches = re.findall(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", text, re.IGNORECASE)
        for email in matches:
            clean = email.strip(".,;:()[]{}")
            if "example." not in clean.lower():
                return clean.lower()
        return ""

    def _extract_department(self, soup: BeautifulSoup, text: str) -> str:
        patterns = [
            r"(Department of [A-Za-z&,\- ]{3,80})",
            r"(School of [A-Za-z&,\- ]{3,80})",
            r"(Faculty of [A-Za-z&,\- ]{3,80})",
            r"(Computer science and operations research)",
        ]
        title_texts = [tag.get_text(" ", strip=True) for tag in soup.find_all(["h1", "h2", "h3", "title", "strong"])[:25]]
        haystack = " ".join(title_texts) + " " + text[:4000]
        for pattern in patterns:
            match = re.search(pattern, haystack, re.IGNORECASE)
            if match:
                return match.group(1).strip(" ,.;:")
        return ""

    def _extract_designation(self, text: str) -> str:
        titles = [
            "Full Professor", "Associate Professor", "Assistant Professor",
            "Professor", "Lecturer", "Senior Lecturer", "Research Scientist",
            "Researcher", "Chair", "Director", "Dean", "Head",
        ]
        for title in titles:
            if re.search(rf"\b{re.escape(title)}\b", text, re.IGNORECASE):
                return title
        return ""

    def _extract_courses(self, text: str) -> List[str]:
        courses = []
        patterns = [
            r"(?:teaches|teaching|courses|coursework|course work)[:\s]+([A-Za-z0-9,&\- /]{6,120})",
            r"\b([A-Z]{2,5}\s*\d{3,4}\s*[-:]\s*[A-Za-z0-9,&\- /]{4,100})",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                course = re.sub(r"\s+", " ", match.group(1)).strip(" ,.;:")
                if 4 < len(course) < 100 and course not in courses:
                    courses.append(course)
                if len(courses) >= 5:
                    return courses
        return courses

    def _extract_location(self, soup: BeautifulSoup, text: str, fallback: str) -> str:
        patterns = [
            r"(?:Office|Room|Building|Location)[:\s]+([A-Za-z0-9,\- .]{5,80})",
            r"(?:Address)[:\s]+([A-Za-z0-9,\- .]{5,120})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip(" ,.;:")
        meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if meta and meta.get("content") and fallback and fallback.lower() not in meta["content"].lower():
            return fallback
        return fallback

    def _resolve_search_result_url(self, href: str) -> str:
        if not href:
            return ""
        if href.startswith("//"):
            return "https:" + href
        if href.startswith("/l/?"):
            parsed = urlparse(href)
            target = parse_qs(parsed.query).get("uddg", [""])[0]
            return unquote(target)
        return href

    def _score_candidate_url(self, url: str, query_name: str, university: str) -> int:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").lower()
        score = 0
        if host.endswith(".edu") or host.endswith(".ac.uk") or host.endswith(".edu.au") or host.endswith(".ac.in"):
            score += 4
        if any(token in path for token in ["/faculty", "/people", "/person", "/profile", "/staff", "/directory"]):
            score += 3
        if any(token in path for token in ["/scholar", "/openalex", "/semantic-scholar", "/orcid"]):
            score -= 6
        if query_name:
            parts = [part.lower() for part in query_name.split() if len(part) > 2]
            score += sum(1 for part in parts if part in url.lower())
        if university:
            for token in re.findall(r"[A-Za-z]{4,}", university.lower()):
                if token in url.lower():
                    score += 1
        return score

    def _search_faculty_pages(self, query_name: str, university: str) -> List[str]:
        query = f'{query_name} {university} faculty email phone'
        try:
            response = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers=self.headers,
                timeout=self.request_timeout,
            )
            if response.status_code != 200:
                return []
            soup = BeautifulSoup(response.text, "html.parser")
            urls = []
            for anchor in soup.select("a.result__a, a[href]"):
                url = self._resolve_search_result_url(anchor.get("href", ""))
                if not url.startswith("http"):
                    continue
                if url not in urls:
                    urls.append(url)
            urls.sort(key=lambda url: self._score_candidate_url(url, query_name, university), reverse=True)
            return urls[:self.search_result_limit]
        except Exception as e:
            logger.warning(f"Faculty page search error: {e}")
            return []

    def _enrich_from_url(self, profile: Dict, url: str) -> Dict:
        enriched = {}
        try:
            response = requests.get(url, headers=self.headers, timeout=self.request_timeout, verify=False)
            if response.status_code != 200 or "text/html" not in response.headers.get("Content-Type", ""):
                return enriched
            soup = BeautifulSoup(response.text, "html.parser")
            text = self._page_text(soup)
            if profile.get("name") and profile["name"].split()[0].lower() not in text.lower():
                return enriched

            email = self._extract_email(text)
            phone, page_location, courses = self._scrape_homepage(url)
            department = self._extract_department(soup, text)
            designation = self._extract_designation(text)
            fallback_university = profile.get("university", "") or (profile.get("affiliations") or [""])[0]
            location = self._extract_location(soup, text, profile.get("location", "") or page_location)

            enriched = {
                "homepage": url,
                "email": email,
                "phone": phone,
                "department": department,
                "designation": designation,
                "course_works": courses,
                "location": location,
                "university": fallback_university,
            }
            return {key: value for key, value in enriched.items() if value}
        except Exception as e:
            logger.warning(f"URL enrichment error for {url}: {e}")
            return {}

    async def enrich_profile(self, profile: Dict) -> Dict:
        university = profile.get("university", "") or (profile.get("affiliations") or [""])[0]
        if not profile.get("name"):
            return profile

        if profile.get("homepage"):
            homepage_data = await asyncio.to_thread(self._enrich_from_url, profile, profile["homepage"])
            if homepage_data:
                profile.update({k: v for k, v in homepage_data.items() if v and not profile.get(k)})
                if profile.get("course_works") or profile.get("email") or profile.get("phone"):
                    return profile

        candidate_urls = await asyncio.to_thread(self._search_faculty_pages, profile["name"], university)
        for url in candidate_urls:
            page_data = await asyncio.to_thread(self._enrich_from_url, profile, url)
            if not page_data:
                continue
            for key, value in page_data.items():
                if value and not profile.get(key):
                    profile[key] = value
            if url and not profile.get("homepage"):
                profile["homepage"] = url
            if profile.get("email") or profile.get("phone") or profile.get("department") or profile.get("course_works"):
                break
        return profile

    # ─────────────────────────────────────────────
    # OPENALEX
    # ─────────────────────────────────────────────
    async def _fetch_openalex(self, name: str, affiliation: Optional[str]) -> List[Dict]:
        params = {"search": name, "per-page": 20, "mailto": "faculty-search@local.dev"}
        try:
            data = await asyncio.to_thread(
                self._request_json,
                "https://api.openalex.org/authors",
                params,
                {},
            )
            results = []
            for a in data.get("results", []):
                affiliations, university, location = self._extract_openalex_affiliations(a)
                concepts = a.get("x_concepts", [])
                research_areas = [c.get("display_name", "") for c in concepts[:6] if c.get("level", 0) <= 2]

                author_id = a.get("id", "").split("/")[-1]
                publications = await asyncio.to_thread(self._fetch_openalex_works, author_id)

                results.append({
                    "source": "openalex",
                    "name": a.get("display_name", ""),
                    "affiliations": affiliations,
                    "university": university,
                    "designation": "",
                    "department": "",
                    "location": location,
                    "email": "",
                    "phone": "",
                    "course_works": [],
                    "paper_count": a.get("works_count", 0),
                    "citation_count": a.get("cited_by_count", 0),
                    "h_index": a.get("summary_stats", {}).get("h_index", 0),
                    "i10_index": a.get("summary_stats", {}).get("i10_index", 0),
                    "source_relevance": float(a.get("relevance_score", 0) or 0),
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

    def _fetch_openalex_works(self, author_id: str) -> List[Dict]:
        """Fetch top publications for an OpenAlex author."""
        try:
            url = "https://api.openalex.org/works"
            params = {
                "filter": f"author.id:{author_id}",
                "sort": "cited_by_count:desc",
                "per-page": 12
            }
            data = self._request_json(url, params, {})
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
            "query": query, "limit": 20,
            "fields": "name,affiliations,paperCount,citationCount,hIndex,homepage,papers.title,papers.year,papers.citationCount,papers.venue"
        }
        try:
            data = await asyncio.to_thread(
                self._request_json,
                "https://api.semanticscholar.org/graph/v1/author/search",
                params,
                {},
            )
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
            data = await asyncio.to_thread(
                self._request_json,
                "https://pub.orcid.org/v3.0/search/",
                {"q": query, "rows": 10},
                {"Accept": "application/json"},
            )
            profiles = []
            for item in (data.get("result", []) or []):
                orcid_id = item.get("orcid-identifier", {}).get("path", "")
                if orcid_id:
                    detail = await asyncio.to_thread(self._fetch_orcid_detail, orcid_id)
                    if detail:
                        profiles.append(detail)
            return profiles
        except Exception as e:
            logger.warning(f"ORCID error: {e}")
            return []

    def _fetch_orcid_detail(self, orcid_id: str) -> Optional[Dict]:
        try:
            data = self._request_json(
                f"https://pub.orcid.org/v3.0/{orcid_id}/record",
                None,
                {"Accept": "application/json"},
            )
            person = data.get("person") or {}
            name_data = person.get("name") or {}
            emails = (person.get("emails") or {}).get("email") or []
            email = emails[0].get("email", "") if emails and isinstance(emails[0], dict) else ""
            activities = data.get("activities-summary") or {}
            employments = (activities.get("employments") or {}).get("affiliation-group") or []
            affiliations, designation, department, university, location = [], "", "", "", ""
            for emp in employments[:3]:
                for s in emp.get("summaries") or []:
                    es = s.get("employment-summary") or {}
                    org = es.get("organization") or {}
                    role = es.get("role-title", "")
                    dept = es.get("department-name", "")
                    org_name = org.get("name", "")
                    addr = org.get("address") or {}
                    city = addr.get("city", "")
                    country = addr.get("country", "")
                    if org_name:
                        affiliations.append(org_name)
                        if not university: university = org_name
                    if role and not designation: designation = role
                    if dept and not department: department = dept
                    if (city or country) and not location:
                        location = f"{city}, {country}".strip(", ")
            works = (activities.get("works") or {}).get("group") or []
            publications = []
            for w in works[:15]:
                summaries = w.get("work-summary") or [{}]
                ws = summaries[0] if summaries else {}
                title = ((ws.get("title") or {}).get("title") or {}).get("value", "")
                year = ((ws.get("publication-date") or {}).get("year") or {}).get("value", "")
                if title:
                    publications.append({"title": title, "year": year, "citations": 0, "venue": ""})
            given = (name_data.get("given-names") or {}).get("value", "")
            family = (name_data.get("family-name") or {}).get("value", "")
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

    def _request_json(self, url: str, params: Optional[Dict], extra_headers: Dict) -> Dict:
        response = requests.get(
            url,
            params=params,
            headers={**self.headers, **extra_headers},
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        return response.json()

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
