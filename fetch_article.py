"""Pobranie pelnej tresci artykulu (Faza 3, OPCJONALNE).

Domyslnie WYLACZONE (config: profile.pelna_tresc: false), bo dokłada zapytania HTTP.
Gdy wlaczone, dla obiecujacych itemow (z sygnalem ceny) pobieramy pelny tekst artykulu,
zeby dokladniej wyciagnac cene/kierunek/date niz z krotkiej zajawki RSS.
"""

import logging
import re

import httpx
from bs4 import BeautifulSoup

import cache

logger = logging.getLogger(__name__)

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
CACHE_MAX_AGE = 60 * 60 * 24   # 24h - tresc artykulu sie nie zmienia
PRICE_HINT = re.compile(r"(\d[\d\s.,]{1,7}\s*(?:z[lł]|pln|eur|usd|€|\$))", re.IGNORECASE)


def looks_dealish(text: str) -> bool:
    """Czy warto pobierac pelna tresc - jest sygnal ceny."""
    return bool(PRICE_HINT.search(text or ""))


def _main_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "aside", "form"]):
        tag.decompose()
    node = soup.find("article") or soup.find("main") or soup
    text = node.get_text(separator="\n")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines)[:8000]


def fetch_text(url: str) -> str:
    """Zwraca oczyszczony tekst artykulu (z cache 24h) albo pusty string przy bledzie."""
    if not url:
        return ""
    cached = cache.get_cached("ART:" + url, CACHE_MAX_AGE)
    if cached is not None:
        return cached
    try:
        resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=15,
                         follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.info("Pelna tresc: nie udalo sie pobrac %s (%s)", url, e)
        return ""
    text = _main_text(resp.text)
    cache.save_cache("ART:" + url, text)
    return text
