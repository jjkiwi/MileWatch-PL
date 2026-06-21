import logging
import time
import urllib.robotparser
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

import cache

logger = logging.getLogger(__name__)

SCRAPE_CACHE_MAX_AGE = 60 * 60 * 6  # 6h - strony promocyjne zmieniaja sie rzadziej
USER_AGENT = "MileWatchPL/0.1 (+https://github.com/jjkiwi/apka2)"
MIN_DELAY_SECONDS = 3  # rate-limit miedzy zadaniami do tej samej domeny

_last_request_at: dict[str, float] = {}


def _robots_allows(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except Exception as e:
        logger.warning("Could not read robots.txt at %s (%s) - blokuje ostroznosciowo", robots_url, e)
        return False
    return rp.can_fetch(USER_AGENT, url)


def _rate_limit(domain: str) -> None:
    last = _last_request_at.get(domain)
    if last is not None:
        elapsed = time.time() - last
        if elapsed < MIN_DELAY_SECONDS:
            time.sleep(MIN_DELAY_SECONDS - elapsed)
    _last_request_at[domain] = time.time()


def _extract_main_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def fetch_scrape_items(name: str, url: str) -> list[dict]:
    """Pobiera strone, wyciaga czysty tekst i zwraca jako jeden surowy item do normalizacji."""
    cached_text = cache.get_cached(url, SCRAPE_CACHE_MAX_AGE)
    if cached_text is not None:
        logger.info("Using cached scrape for %s", name)
        text = cached_text
    else:
        if not _robots_allows(url):
            logger.warning("robots.txt disallows scraping %s - skipping", url)
            return []

        domain = urlparse(url).netloc
        _rate_limit(domain)

        logger.info("Scraping %s (%s)", name, url)
        try:
            resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=20, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("Scrape fetch failed for %s: %s", name, e)
            return []

        text = _extract_main_text(resp.text)
        cache.save_cache(url, text)

    if not text.strip():
        return []

    return [
        {
            "tekst": text,
            "zrodlo_url": url,
            "zrodlo_nazwa": name,
        }
    ]
