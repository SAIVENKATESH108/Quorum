"""
Research Studio — source provider abstraction and verified free-tier implementations.

Only integrates providers whose endpoints and response shapes were verified
against their public documentation before this implementation:
  - CrossRef  : https://api.crossref.org/swagger-ui/index.html  (already used in researcher.py)
  - OpenAlex  : https://docs.openalex.org/api-entities/works/search-works
  - arXiv     : https://info.arxiv.org/help/api/basics.html
  - Semantic Scholar: https://api.semanticscholar.org/api-docs/

NOT claimed as available: IEEE Xplore, Google Scholar, PubMed (requires NCBI API key),
Nature, Springer, Scopus, or any other paid/login-gated service.
"""

from __future__ import annotations

import logging
import urllib.parse
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import re
import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DOI Utilities
# ---------------------------------------------------------------------------

DOI_REGEX = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")


def extract_doi(text: Optional[str]) -> Optional[str]:
    """Extract and validate standard DOI from raw string or DOI URL."""
    if not text:
        return None
    cleaned = text.strip()
    prefixes = [
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    ]
    for prefix in prefixes:
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break
    if DOI_REGEX.match(cleaned):
        return cleaned
    return None


def validate_doi(doi: Optional[str]) -> bool:
    """Check if given string represents a valid syntax conforming DOI."""
    return extract_doi(doi) is not None


@dataclass
class SourceCandidate:
    """Normalised metadata record retrieved from a research source provider."""

    provider: str                          # e.g. "crossref", "openalex", "arxiv"
    identifier: Optional[str]             # DOI, arXiv ID, or OpenAlex Work ID
    canonical_url: str                    # Permanent URL to the source
    title: str
    authors: List[str] = field(default_factory=list)
    publisher: Optional[str] = None
    publication_date: Optional[str] = None  # ISO 8601 partial date "YYYY" or "YYYY-MM-DD"
    abstract: Optional[str] = None
    access_level: str = "metadata_only"   # full_text | abstract_only | snippet_only | metadata_only
    source_class: str = "unverified"      # peer_reviewed | preprint | gov_standards | tech_pub | news | user_provided
    retrieval_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    inclusion_reason: Optional[str] = None
    exclusion_reason: Optional[str] = None


@dataclass
class ProviderSearchResult:
    """Outcome of a single provider search call."""

    provider_name: str
    query: str
    candidates: List[SourceCandidate]
    success: bool
    error: Optional[str] = None
    retrieved_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    total_results_reported: int = 0


# ---------------------------------------------------------------------------
# Abstract Base
# ---------------------------------------------------------------------------

class ResearchSourceProvider(ABC):
    """
    Strategy interface for research source providers.

    Concrete implementations must only use documented, publicly available,
    permitted endpoints. They must never invent search results, titles, DOIs,
    authors, or any other metadata.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name of this provider."""

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> ProviderSearchResult:
        """Execute a search and return normalised candidates."""

    @property
    def source_capabilities(self) -> List[str]:
        """List of capabilities supported by this provider (e.g., search, metadata, full_text)."""
        return ["search", "metadata"]

    @property
    def default_source_class(self) -> str:
        """Default classification for items returned by this provider."""
        return "peer_reviewed"

    async def fetch_source(self, identifier_or_url: str) -> Optional[SourceCandidate]:
        """Fetch metadata for a single specific identifier or URL."""
        return None

    def normalize(self, raw_result: Any) -> Optional[SourceCandidate]:
        """Normalize raw provider record into a standardized SourceCandidate."""
        return None

    async def health_check(self) -> bool:
        """Ping the provider to confirm it is reachable. Returns True if OK."""
        return False


# ---------------------------------------------------------------------------
# CrossRef (polite pool — already used in researcher.py)
# ---------------------------------------------------------------------------

class CrossRefProvider(ResearchSourceProvider):
    """
    CrossRef REST API — peer-reviewed literature metadata.
    Endpoint: https://api.crossref.org/works
    Auth: none (polite pool requires a mailto: User-Agent)
    Docs: https://api.crossref.org/swagger-ui/index.html
    """

    provider_name = "CrossRef"
    BASE_URL = "https://api.crossref.org"
    USER_AGENT = "QuorumResearchStudio/1.0 (mailto:team@quorum.ai; polite-pool)"

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> ProviderSearchResult:
        candidates: List[SourceCandidate] = []
        params: Dict[str, Any] = {
            "query": query[:200],
            "rows": min(max_results, 10),
            "select": "DOI,title,author,publisher,published,abstract,container-title,URL,type",
        }
        if date_from:
            params["filter"] = f"from-pub-date:{date_from[:4]}"

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/works",
                    params=params,
                    headers={"User-Agent": self.USER_AGENT},
                )
                resp.raise_for_status()
                items = resp.json().get("message", {}).get("items", [])
                total = resp.json().get("message", {}).get("total-results", 0)

            for item in items:
                doi = item.get("DOI", "")
                title_list = item.get("title", [])
                title = title_list[0] if title_list else ""
                if not title or not doi:
                    continue  # skip entries without both
                url = item.get("URL") or f"https://doi.org/{doi}"
                authors = [
                    f"{a.get('given', '')} {a.get('family', '')}".strip()
                    for a in (item.get("author") or [])[:6]
                    if a.get("family")
                ]
                pub = item.get("published", {}).get("date-parts", [[]])[0]
                pub_date = "-".join(str(p) for p in pub) if pub else None
                container = (item.get("container-title") or [None])[0]
                abstract_raw = item.get("abstract", "")
                # CrossRef abstracts may contain JATS XML tags — strip simply
                import re
                abstract = re.sub(r"<[^>]+>", " ", abstract_raw).strip() if abstract_raw else None

                candidates.append(SourceCandidate(
                    provider="crossref",
                    identifier=doi,
                    canonical_url=url,
                    title=title,
                    authors=authors,
                    publisher=container or item.get("publisher"),
                    publication_date=pub_date,
                    abstract=abstract,
                    access_level="abstract_only" if abstract else "metadata_only",
                    source_class="peer_reviewed",
                    raw_metadata=item,
                    inclusion_reason="Returned by CrossRef DOI index for query match",
                ))

            return ProviderSearchResult(
                provider_name=self.provider_name,
                query=query,
                candidates=candidates,
                success=True,
                total_results_reported=total,
            )

        except Exception as exc:
            logger.warning(f"[CrossRef] search failed for '{query}': {exc}")
            return ProviderSearchResult(
                provider_name=self.provider_name,
                query=query,
                candidates=[],
                success=False,
                error=str(exc),
            )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{self.BASE_URL}/works",
                    params={"query": "test", "rows": 1},
                    headers={"User-Agent": self.USER_AGENT},
                )
                return r.status_code == 200
        except Exception:
            return False


# ---------------------------------------------------------------------------
# OpenAlex (free, CC0 — no API key required)
# ---------------------------------------------------------------------------

class OpenAlexProvider(ResearchSourceProvider):
    """
    OpenAlex open scholarly graph API.
    Endpoint: https://api.openalex.org/works
    Auth: none (email in User-Agent for polite pool)
    Docs: https://docs.openalex.org/api-entities/works/search-works
    License: CC0 (metadata freely reusable)
    """

    provider_name = "OpenAlex"
    BASE_URL = "https://api.openalex.org"
    USER_AGENT = "QuorumResearchStudio/1.0 (mailto:team@quorum.ai)"

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> ProviderSearchResult:
        candidates: List[SourceCandidate] = []
        params: Dict[str, Any] = {
            "search": query[:300],
            "per-page": min(max_results, 10),
            "select": "id,doi,title,authorships,publication_date,primary_location,open_access,abstract_inverted_index,type",
        }
        if date_from:
            year = date_from[:4]
            params["filter"] = f"publication_year:>{int(year)-1}"

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/works",
                    params=params,
                    headers={"User-Agent": self.USER_AGENT},
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                total = data.get("meta", {}).get("count", 0)

            for item in results:
                title = item.get("title", "")
                if not title:
                    continue
                doi = item.get("doi", "")
                if doi and doi.startswith("https://doi.org/"):
                    doi = doi[len("https://doi.org/"):]
                canonical = item.get("doi") or item.get("id", "")
                authors = [
                    a.get("author", {}).get("display_name", "")
                    for a in (item.get("authorships") or [])[:6]
                    if a.get("author", {}).get("display_name")
                ]
                pub_date = item.get("publication_date")
                primary = item.get("primary_location") or {}
                publisher = (primary.get("source") or {}).get("display_name")
                oa_url = (item.get("open_access") or {}).get("oa_url")
                url = oa_url or (f"https://doi.org/{doi}" if doi else canonical)

                # Reconstruct abstract from inverted index if present
                inv = item.get("abstract_inverted_index")
                abstract: Optional[str] = None
                if inv and isinstance(inv, dict):
                    try:
                        max_pos = max(pos for positions in inv.values() for pos in positions)
                        words_arr = [""] * (max_pos + 1)
                        for word, positions in inv.items():
                            for pos in positions:
                                words_arr[pos] = word
                        abstract = " ".join(words_arr).strip()
                    except Exception:
                        pass

                source_type = item.get("type", "")
                source_class = "peer_reviewed" if source_type in ("journal-article", "book-chapter") else (
                    "preprint" if source_type in ("preprint",) else "tech_pub"
                )

                candidates.append(SourceCandidate(
                    provider="openalex",
                    identifier=doi or item.get("id"),
                    canonical_url=url,
                    title=title,
                    authors=authors,
                    publisher=publisher,
                    publication_date=pub_date,
                    abstract=abstract,
                    access_level="abstract_only" if abstract else "metadata_only",
                    source_class=source_class,
                    raw_metadata=item,
                    inclusion_reason="OpenAlex CC0 scholarly index match",
                ))

            return ProviderSearchResult(
                provider_name=self.provider_name,
                query=query,
                candidates=candidates,
                success=True,
                total_results_reported=total,
            )

        except Exception as exc:
            logger.warning(f"[OpenAlex] search failed for '{query}': {exc}")
            return ProviderSearchResult(
                provider_name=self.provider_name,
                query=query,
                candidates=[],
                success=False,
                error=str(exc),
            )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{self.BASE_URL}/works",
                    params={"search": "test", "per-page": 1},
                    headers={"User-Agent": self.USER_AGENT},
                )
                return r.status_code == 200
        except Exception:
            return False


# ---------------------------------------------------------------------------
# arXiv (free Atom feed API)
# ---------------------------------------------------------------------------

class ArXivProvider(ResearchSourceProvider):
    """
    arXiv preprint API.
    Endpoint: https://export.arxiv.org/api/query
    Auth: none
    Docs: https://info.arxiv.org/help/api/basics.html
    Permitted use: search and retrieval of metadata.
    """

    provider_name = "arXiv"
    default_source_class = "preprint"
    BASE_URL = "https://export.arxiv.org/api/query"

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> ProviderSearchResult:
        import xml.etree.ElementTree as ET
        candidates: List[SourceCandidate] = []
        safe_query = urllib.parse.quote_plus(query[:200])
        url = (
            f"{self.BASE_URL}?search_query=all:{safe_query}"
            f"&max_results={min(max_results, 10)}"
            f"&sortBy=relevance&sortOrder=descending"
        )

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()

            NS = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom",
            }
            root = ET.fromstring(resp.text)
            entries = root.findall("atom:entry", NS)
            total_el = root.find("{http://a9.com/-/spec/opensearch/1.1/}totalResults")
            total = int(total_el.text) if total_el is not None and total_el.text else 0

            for entry in entries:
                title_el = entry.find("atom:title", NS)
                title = title_el.text.strip().replace("\n", " ") if title_el is not None else ""
                if not title:
                    continue

                id_el = entry.find("atom:id", NS)
                arxiv_id_url = id_el.text.strip() if id_el is not None else ""
                # Extract bare arXiv ID: "http://arxiv.org/abs/2301.12345v1" -> "2301.12345"
                arxiv_id = arxiv_id_url.split("/abs/")[-1].split("v")[0] if "/abs/" in arxiv_id_url else ""
                canonical = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else arxiv_id_url

                abstract_el = entry.find("atom:summary", NS)
                abstract = abstract_el.text.strip().replace("\n", " ") if abstract_el is not None else None

                authors = [
                    (a.find("atom:name", NS).text or "").strip()
                    for a in entry.findall("atom:author", NS)
                    if a.find("atom:name", NS) is not None
                ][:6]

                pub_el = entry.find("atom:published", NS)
                pub_date = pub_el.text[:10] if pub_el is not None and pub_el.text else None

                candidates.append(SourceCandidate(
                    provider="arxiv",
                    identifier=f"arXiv:{arxiv_id}" if arxiv_id else None,
                    canonical_url=canonical,
                    title=title,
                    authors=authors,
                    publisher="arXiv preprint server",
                    publication_date=pub_date,
                    abstract=abstract,
                    access_level="abstract_only" if abstract else "metadata_only",
                    source_class="preprint",
                    raw_metadata={"arxiv_id": arxiv_id, "url": canonical},
                    inclusion_reason="arXiv preprint match via Atom API",
                ))

            return ProviderSearchResult(
                provider_name=self.provider_name,
                query=query,
                candidates=candidates,
                success=True,
                total_results_reported=total,
            )

        except Exception as exc:
            logger.warning(f"[arXiv] search failed for '{query}': {exc}")
            return ProviderSearchResult(
                provider_name=self.provider_name,
                query=query,
                candidates=[],
                success=False,
                error=str(exc),
            )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.BASE_URL}?search_query=all:test&max_results=1")
                return r.status_code == 200
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Semantic Scholar (free academic graph — no key required for basic search)
# ---------------------------------------------------------------------------

class SemanticScholarProvider(ResearchSourceProvider):
    """
    Semantic Scholar Academic Graph API.
    Endpoint: https://api.semanticscholar.org/graph/v1/paper/search
    Auth: none for public search (rate-limited to ~100 req/5min without key)
    Docs: https://api.semanticscholar.org/api-docs/
    Permitted use: metadata and abstract retrieval.
    """

    provider_name = "Semantic Scholar"
    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> ProviderSearchResult:
        candidates: List[SourceCandidate] = []
        params: Dict[str, Any] = {
            "query": query[:300],
            "limit": min(max_results, 10),
            "fields": "paperId,externalIds,title,abstract,authors,year,publicationDate,"
                      "publicationVenue,openAccessPdf,publicationTypes",
        }
        if date_from:
            params["year"] = f"{date_from[:4]}-"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/paper/search",
                    params=params,
                    headers={"User-Agent": "QuorumResearchStudio/1.0"},
                )
                if resp.status_code == 429:
                    return ProviderSearchResult(
                        provider_name=self.provider_name,
                        query=query,
                        candidates=[],
                        success=False,
                        error="Rate limited by Semantic Scholar (no API key configured)",
                    )
                resp.raise_for_status()
                data = resp.json()
                papers = data.get("data", [])
                total = data.get("total", 0)

            for paper in papers:
                title = paper.get("title", "")
                if not title:
                    continue
                ext = paper.get("externalIds") or {}
                doi = ext.get("DOI")
                arxiv_id = ext.get("ArXiv")
                canonical = (
                    (f"https://doi.org/{doi}") if doi else
                    (f"https://arxiv.org/abs/{arxiv_id}") if arxiv_id else
                    f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}"
                )
                authors = [
                    a.get("name", "")
                    for a in (paper.get("authors") or [])[:6]
                    if a.get("name")
                ]
                venue_obj = paper.get("publicationVenue") or {}
                publisher = venue_obj.get("name")
                pub_date = paper.get("publicationDate") or (
                    str(paper.get("year")) if paper.get("year") else None
                )
                abstract = paper.get("abstract")
                pub_types = paper.get("publicationTypes") or []
                source_class = (
                    "peer_reviewed" if any(t in ("JournalArticle", "Conference") for t in pub_types)
                    else "preprint"
                )

                candidates.append(SourceCandidate(
                    provider="semanticscholar",
                    identifier=doi or f"S2:{paper.get('paperId', '')}",
                    canonical_url=canonical,
                    title=title,
                    authors=authors,
                    publisher=publisher,
                    publication_date=pub_date,
                    abstract=abstract,
                    access_level="abstract_only" if abstract else "metadata_only",
                    source_class=source_class,
                    raw_metadata=paper,
                    inclusion_reason="Semantic Scholar academic graph match",
                ))

            return ProviderSearchResult(
                provider_name=self.provider_name,
                query=query,
                candidates=candidates,
                success=True,
                total_results_reported=total,
            )

        except Exception as exc:
            logger.warning(f"[SemanticScholar] search failed for '{query}': {exc}")
            return ProviderSearchResult(
                provider_name=self.provider_name,
                query=query,
                candidates=[],
                success=False,
                error=str(exc),
            )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{self.BASE_URL}/paper/search",
                    params={"query": "neural network", "limit": 1, "fields": "title"},
                )
                return r.status_code in (200, 429)  # 429 means reachable but rate-limited
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Provider Registry
# ---------------------------------------------------------------------------

DEFAULT_PROVIDERS: List[ResearchSourceProvider] = [
    CrossRefProvider(),
    OpenAlexProvider(),
    ArXivProvider(),
    SemanticScholarProvider(),
]


async def check_all_providers() -> Dict[str, bool]:
    """Return availability status for all registered providers."""
    import asyncio
    results = await asyncio.gather(
        *[p.health_check() for p in DEFAULT_PROVIDERS],
        return_exceptions=True,
    )
    return {
        p.provider_name: bool(r) if not isinstance(r, Exception) else False
        for p, r in zip(DEFAULT_PROVIDERS, results)
    }
