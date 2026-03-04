"""Lyrics fetching: Lyrics.ovh (primary) → Genius HTML scraping (fallback).

Both functions are async and use httpx. The Genius fallback requires
GENIUS_API_KEY to be set; when absent the fallback is silently skipped.
"""

from __future__ import annotations

import logging
import re
import urllib.parse

import httpx

from . import config
from .puzzle import clean_lyrics, extract_excerpt

logger = logging.getLogger(__name__)


async def _fetch_lyrics_ovh(artist: str, title: str) -> str | None:
    """Try Lyrics.ovh free API. Returns raw lyrics string or None."""
    url = f"https://api.lyrics.ovh/v1/{urllib.parse.quote(artist)}/{urllib.parse.quote(title)}"
    try:
        async with httpx.AsyncClient(timeout=config.LYRICS_OVH_TIMEOUT) as client:
            r = await client.get(url)
        if r.status_code == 200:
            data = r.json()
            lyrics = data.get("lyrics", "").strip()
            if lyrics:
                logger.info("[lyrics] lyrics.ovh hit: %s - %s", artist, title)
                return lyrics
    except Exception as exc:
        logger.warning("[lyrics] lyrics.ovh error for %s - %s: %s", artist, title, exc)
    return None


async def _fetch_genius(artist: str, title: str) -> str | None:
    """Try Genius API: search → scrape HTML. Requires GENIUS_API_KEY."""
    if not config.GENIUS_API_KEY:
        return None

    try:
        from bs4 import BeautifulSoup  # noqa: PLC0415
    except ImportError:
        logger.warning("[lyrics] beautifulsoup4 not installed — Genius fallback disabled.")
        return None

    query = f"{artist} {title}"
    search_url = "https://api.genius.com/search"
    headers = {"Authorization": f"Bearer {config.GENIUS_API_KEY}"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(search_url, params={"q": query}, headers=headers)
        if r.status_code != 200:
            logger.warning("[lyrics] Genius search failed: %s", r.status_code)
            return None

        hits = r.json().get("response", {}).get("hits", [])
        if not hits:
            logger.info("[lyrics] Genius: no results for %s - %s", artist, title)
            return None

        song_url = hits[0]["result"]["url"]
        logger.info("[lyrics] Genius scraping: %s", song_url)

        async with httpx.AsyncClient(
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True,
        ) as client:
            page = await client.get(song_url)

        soup = BeautifulSoup(page.text, "lxml")
        containers = soup.find_all("div", attrs={"data-lyrics-container": "true"})
        if not containers:
            logger.warning("[lyrics] Genius: no lyrics container found at %s", song_url)
            return None

        lines = []
        for container in containers:
            for br in container.find_all("br"):
                br.replace_with("\n")
            lines.append(container.get_text())

        lyrics = "\n".join(lines).strip()
        if lyrics:
            logger.info("[lyrics] Genius hit: %s - %s", artist, title)
            return lyrics

    except Exception as exc:
        logger.warning("[lyrics] Genius error for %s - %s: %s", artist, title, exc)

    return None


async def fetch_lyrics(artist: str, title: str) -> str | None:
    """Fetch lyrics for a song, returning a cleaned excerpt or None.

    Chain: Lyrics.ovh → Genius → None.
    The returned string is cleaned and truncated to MAX_LYRICS_LINES.
    """
    raw = await _fetch_lyrics_ovh(artist, title)
    if not raw:
        raw = await _fetch_genius(artist, title)
    if not raw:
        logger.warning("[lyrics] All sources failed for %s - %s", artist, title)
        return None

    cleaned = clean_lyrics(raw)
    excerpt = extract_excerpt(cleaned, max_lines=config.MAX_LYRICS_LINES)
    return excerpt
