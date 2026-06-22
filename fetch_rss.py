import logging

import feedparser
import httpx

import cache

logger = logging.getLogger(__name__)

RSS_CACHE_MAX_AGE = 60 * 60  # 1h - feedy RSS zmieniaja sie czesto, ale nie co minute
# Realistyczny User-Agent przegladarki - niektore serwisy (np. Reisetopia) odrzucaja
# nietypowe UA bledem 403. Czytamy wylacznie publiczne feedy, w malej liczbie zapytan.
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")


def fetch_rss_items(name: str, url: str) -> list[dict]:
    """Pobiera wpisy z feedu RSS. Zwraca liste surowych itemow do normalizacji."""
    raw_xml = cache.get_cached(url, RSS_CACHE_MAX_AGE)
    if raw_xml is None:
        logger.info("Fetching RSS %s (%s)", name, url)
        try:
            resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=15, follow_redirects=True)
            resp.raise_for_status()
            raw_xml = resp.text
            cache.save_cache(url, raw_xml)
        except httpx.HTTPError as e:
            logger.warning("RSS fetch failed for %s: %s", name, e)
            return []
    else:
        logger.info("Using cached RSS for %s", name)

    parsed = feedparser.parse(raw_xml)
    items = []
    for entry in parsed.entries:
        items.append(
            {
                "tekst": f"{entry.get('title', '')}\n\n{entry.get('summary', '')}",
                "zrodlo_url": entry.get("link", url),
                "zrodlo_nazwa": name,
            }
        )
    return items
