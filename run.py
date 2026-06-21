import logging
import os
import sys
import uuid

import anthropic
from dotenv import load_dotenv

import dedup
import digest
import storage
from fetch_rss import fetch_rss_items
from fetch_scrape import fetch_scrape_items
from normalize import normalize_item
from sources import load_profile, load_sources

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("run")


def fetch_all(sources: list) -> list[dict]:
    raw_items = []
    for source in sources:
        if source.type == "rss":
            items = fetch_rss_items(source.name, source.url)
        elif source.type == "scrape":
            items = fetch_scrape_items(source.name, source.url)
        else:
            logger.warning("Nieznany typ zrodla: %s (%s)", source.type, source.name)
            continue
        logger.info("Zrodlo %s: %d surowych itemow", source.name, len(items))
        raw_items.extend(items)
    return raw_items


def main() -> int:
    load_dotenv()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("Brak ANTHROPIC_API_KEY w zmiennych srodowiskowych. Ustaw go w .env lub eksportuj.")
        return 1

    sources = load_sources()
    profile = load_profile()
    logger.info("Wczytano %d aktywnych zrodel", len(sources))

    raw_items = fetch_all(sources)
    logger.info("Razem zebrano %d surowych itemow do normalizacji", len(raw_items))

    client = anthropic.Anthropic()
    candidates = []
    for raw_item in raw_items:
        candidates.extend(normalize_item(client, raw_item))
    logger.info("Normalizacja: wykryto %d kandydatow na promocje", len(candidates))

    for promo in candidates:
        promo.id = str(uuid.uuid4())

    conn = storage.connect()
    existing = storage.get_recent_promotions(conn)
    unique = dedup.dedup_promotions(candidates, existing)

    new_promotions = []
    for promo in unique:
        if storage.save_promotion(conn, promo):
            new_promotions.append(promo)
    logger.info("Zapisano %d nowych promocji do bazy", len(new_promotions))

    relevant = digest.filter_for_profile(new_promotions, profile)
    print()
    print(digest.format_digest(relevant))

    return 0


if __name__ == "__main__":
    sys.exit(main())
