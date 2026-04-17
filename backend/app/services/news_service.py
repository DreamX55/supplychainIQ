"""
Live News Service for SupplyChainIQ
Fetches supply-chain-relevant articles from free RSS feeds (no API key required).
Falls back gracefully to an empty list on any network or parse error.

Feeds used:
  - Reuters Business/World
  - BBC Business
  - Financial Times (public RSS)
  - The Guardian Business

Caches results for CACHE_TTL_SECONDS to avoid hammering sources on every sidebar refresh.
"""

import asyncio
import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("supplychainiq.news")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CACHE_TTL_SECONDS = 30 * 60  # refresh every 30 minutes

RSS_FEEDS = [
    {
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "source": "Reuters",
        "category": "logistics",
    },
    {
        "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "source": "BBC Business",
        "category": "geopolitical",
    },
    {
        "url": "https://www.theguardian.com/business/rss",
        "source": "The Guardian",
        "category": "geopolitical",
    },
    {
        "url": "https://www.ft.com/rss/home",
        "source": "Financial Times",
        "category": "logistics",
    },
]

# Keywords that flag an article as supply-chain-relevant
SUPPLY_CHAIN_KEYWORDS = [
    "supply chain", "shipping", "port", "freight", "logistics",
    "semiconductor", "chip", "tariff", "trade", "manufacturing",
    "red sea", "suez", "taiwan", "sanctions", "disruption",
    "inflation", "shortage", "inventory", "geopolitic", "export",
    "import", "warehouse", "container", "cargo",
]

# Keyword → region mapping (first match wins)
REGION_KEYWORDS: Dict[str, str] = {
    "taiwan": "Taiwan",
    "china": "China",
    "red sea": "Red Sea",
    "suez": "Suez Canal",
    "vietnam": "Vietnam",
    "india": "India",
    "ukraine": "Eastern Europe",
    "russia": "Russia",
    "singapore": "Singapore",
    "rotterdam": "Rotterdam",
    "panama": "Panama Canal",
    "south china sea": "South China Sea",
    "los angeles": "Los Angeles/Long Beach",
    "long beach": "Los Angeles/Long Beach",
    "japan": "Japan",
    "korea": "South Korea",
    "europe": "Europe",
    "germany": "Germany",
    "middle east": "Middle East",
    "africa": "Africa",
    "brazil": "Brazil",
}

# Keyword → severity mapping (highest match wins)
SEVERITY_KEYWORDS: Dict[str, str] = {
    "critical": "Critical",
    "war": "Critical",
    "attack": "High",
    "blockade": "Critical",
    "crisis": "High",
    "disruption": "High",
    "shortage": "High",
    "tariff": "Medium",
    "sanction": "High",
    "strike": "High",
    "delay": "Medium",
    "congestion": "Medium",
    "growth": "Low",
    "stable": "Low",
    "recovery": "Low",
}

SEVERITY_RANK = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}


def _infer_region(text: str) -> str:
    lower = text.lower()
    for kw, region in REGION_KEYWORDS.items():
        if kw in lower:
            return region
    return "Global"


def _infer_severity(text: str) -> str:
    lower = text.lower()
    best = "Medium"
    best_rank = SEVERITY_RANK["Medium"]
    for kw, sev in SEVERITY_KEYWORDS.items():
        if kw in lower:
            rank = SEVERITY_RANK.get(sev, 0)
            if rank > best_rank:
                best = sev
                best_rank = rank
    return best


def _is_relevant(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in SUPPLY_CHAIN_KEYWORDS)


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str[:19], fmt[:len(date_str)])
        except Exception:
            pass
    return None


def _parse_rss(xml_text: str, source: str, default_category: str) -> List[Dict[str, Any]]:
    """Parse an RSS 2.0 / Atom feed and return normalised article dicts."""
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("RSS parse error (%s): %s", source, exc)
        return items

    ns = {"atom": "http://www.w3.org/2005/Atom"}

    # RSS 2.0 — <item> elements
    for item in root.iter("item"):
        title_el = item.find("title")
        desc_el = item.find("description")
        date_el = item.find("pubDate")
        link_el = item.find("link")

        title = (title_el.text or "").strip() if title_el is not None else ""
        desc = (desc_el.text or "").strip() if desc_el is not None else ""
        combined = f"{title} {desc}"

        if not _is_relevant(combined):
            continue

        pub_date = _parse_date(date_el.text if date_el is not None else None)
        date_str = pub_date.strftime("%Y-%m-%d") if pub_date else datetime.now(timezone.utc).strftime("%Y-%m-%d")

        items.append({
            "title": title,
            "description": desc[:300] + ("…" if len(desc) > 300 else ""),
            "region": _infer_region(combined),
            "category": default_category,
            "risk_level": _infer_severity(combined),
            "last_updated": date_str,
            "sources": [source],
            "link": (link_el.text or "").strip() if link_el is not None else "",
        })

    # Atom — <entry> elements (FT uses Atom)
    for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
        title_el = entry.find("{http://www.w3.org/2005/Atom}title")
        summary_el = entry.find("{http://www.w3.org/2005/Atom}summary")
        updated_el = entry.find("{http://www.w3.org/2005/Atom}updated")
        link_el = entry.find("{http://www.w3.org/2005/Atom}link")

        title = (title_el.text or "").strip() if title_el is not None else ""
        desc = (summary_el.text or "").strip() if summary_el is not None else ""
        combined = f"{title} {desc}"

        if not _is_relevant(combined):
            continue

        pub_date = _parse_date(updated_el.text if updated_el is not None else None)
        date_str = pub_date.strftime("%Y-%m-%d") if pub_date else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        link = link_el.get("href", "") if link_el is not None else ""

        items.append({
            "title": title,
            "description": desc[:300] + ("…" if len(desc) > 300 else ""),
            "region": _infer_region(combined),
            "category": default_category,
            "risk_level": _infer_severity(combined),
            "last_updated": date_str,
            "sources": [source],
            "link": link,
        })

    return items


# ---------------------------------------------------------------------------
# Cache & fetcher
# ---------------------------------------------------------------------------

_cache: List[Dict[str, Any]] = []
_cache_time: float = 0.0
_fetch_lock = asyncio.Lock()


async def _fetch_feed(client: httpx.AsyncClient, feed: Dict[str, str]) -> List[Dict[str, Any]]:
    try:
        resp = await client.get(feed["url"], timeout=8.0, follow_redirects=True)
        resp.raise_for_status()
        return _parse_rss(resp.text, feed["source"], feed["category"])
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", feed["url"], exc)
        return []


async def get_live_alerts(limit: int = 12) -> List[Dict[str, Any]]:
    """
    Return live supply-chain risk articles from RSS feeds, deduplicated and
    sorted newest-first.  Results are cached for CACHE_TTL_SECONDS.
    """
    global _cache, _cache_time

    async with _fetch_lock:
        now = time.monotonic()
        if _cache and (now - _cache_time) < CACHE_TTL_SECONDS:
            logger.debug("Returning cached news feed (%d items)", len(_cache))
            return _cache[:limit]

        logger.info("Refreshing live news feed from %d RSS sources…", len(RSS_FEEDS))
        articles: List[Dict[str, Any]] = []

        async with httpx.AsyncClient(
            headers={"User-Agent": "SupplyChainIQ/3.0 supply-chain-risk-monitor"},
        ) as client:
            results = await asyncio.gather(
                *[_fetch_feed(client, feed) for feed in RSS_FEEDS],
                return_exceptions=True,
            )

        for result in results:
            if isinstance(result, list):
                articles.extend(result)

        # Deduplicate by title similarity (first 60 chars)
        seen: set = set()
        deduped = []
        for a in articles:
            key = a["title"][:60].lower().strip()
            if key and key not in seen:
                seen.add(key)
                deduped.append(a)

        # Sort by date descending, assign stable IDs
        deduped.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
        for i, a in enumerate(deduped):
            a.setdefault("id", f"live_{i:04d}")

        if deduped:
            _cache = deduped
            _cache_time = now
            logger.info("Live news feed refreshed: %d relevant articles", len(deduped))
        else:
            logger.warning("No live articles retrieved — keeping previous cache or returning empty")

        return _cache[:limit]
