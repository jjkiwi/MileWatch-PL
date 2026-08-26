"""Pipeline MileWatch PL - w pelni darmowy, bez zadnego API.

Fetch (RSS + scrape) -> Extract (slowa kluczowe) -> Dedup -> Storage -> Digest.
Opcjonalnie: alert Telegram (jesli ustawiono zmienne srodowiskowe - darmowe).

Uzycie:
    python run.py                  # pelny przebieg, wypisuje digest w terminalu
    from run import run_pipeline   # uzywane przez aplikacje desktop (gui.py)
"""

import logging
import os
import sys
import uuid

import dedup
import digest
import golden
import storage
import telegram_alert
from deals import detect_deal
from extract import extract_from_item
from fetch_rss import fetch_rss_items
from fetch_scrape import fetch_scrape_items
from sources import load_profile, load_sources

try:
    from dotenv import load_dotenv
except ImportError:  # dotenv jest opcjonalny - bez niego po prostu czytamy os.environ
    def load_dotenv():
        return False

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


def run_pipeline(progress=None) -> list:
    """Wykonuje pelny przebieg i zwraca liste NOWO zapisanych promocji.

    progress: opcjonalna funkcja(str) do raportowania postepu (uzywana przez GUI).
    Nie wymaga zadnego klucza API - dziala w 100% za darmo.
    """
    def _say(msg: str) -> None:
        logger.info(msg)
        if progress:
            progress(msg)

    sources = load_sources()
    _say(f"Wczytano {len(sources)} aktywnych zrodel")

    raw_items = fetch_all(sources)
    _say(f"Zebrano {len(raw_items)} surowych itemow")

    profile = load_profile()
    use_fulltext = bool(profile.get("pelna_tresc"))
    if use_fulltext:
        import fetch_article
    windows = golden.load_windows(profile)   # zlote terminy (okna urlopowe)
    if windows:
        _say(f"Zlote terminy: {len(windows)} okien urlopowych")

    candidates = []
    golden_hits = 0
    for raw_item in raw_items:
        # Faza 3 (opcjonalnie): dla itemow z sygnalem ceny dociagnij pelna tresc artykulu,
        # zeby dokladniej wyciagnac cene/kierunek/date niz z krotkiej zajawki RSS.
        if use_fulltext and fetch_article.looks_dealish(raw_item.get("tekst", "")):
            full = fetch_article.fetch_text(raw_item.get("zrodlo_url", ""))
            if full:
                raw_item = {**raw_item, "tekst": raw_item.get("tekst", "") + "\n" + full}

        item_promos = extract_from_item(raw_item)        # promocje Miles & More
        deal = detect_deal(raw_item)                     # bledy cenowe / tani lot / biznes
        if deal:
            item_promos.append(deal)

        # Zlote terminy: jesli termin podrozy w tekscie wpada w okno urlopowe, oznacz
        # wszystkie promocje z tego itemu (zawsze alertowane, podbite w scoringu).
        if windows:
            gm = golden.match(raw_item.get("tekst", ""), windows)
            if gm:
                for promo in item_promos:
                    golden.tag(promo, gm)
                golden_hits += len(item_promos)

        candidates.extend(item_promos)
    msg = f"Wykryto {len(candidates)} kandydatow na promocje"
    if windows:
        msg += f" (w tym {golden_hits} w zlotym terminie)"
    _say(msg)

    for promo in candidates:
        promo.id = str(uuid.uuid4())

    conn = storage.connect()
    existing = storage.get_recent_promotions(conn)
    unique = dedup.dedup_promotions(candidates, existing)

    import baseline
    new_promotions = []
    for promo in unique:
        # Baseline cen (Faza 3): ocena PRZED zapisem (moze oznaczyc "Rekord cenowy"),
        # a zapis obserwacji do historii dopiero po udanym zapisie nowej promocji.
        obs = baseline.assess(conn, promo)
        if storage.save_promotion(conn, promo):
            new_promotions.append(promo)
            baseline.record(conn, obs)
    _say(f"Zapisano {len(new_promotions)} nowych promocji")

    # Opcjonalne alerty - Telegram i/lub Signal (oba w pelni darmowe). Kazdy kanal wlacza
    # sie samodzielnie, gdy ustawione sa jego zmienne srodowiskowe.
    profile = load_profile()
    _send_alerts(conn, profile, _say)

    conn.close()
    return new_promotions


def _send_alerts(conn, profile, say) -> None:
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID")
    sig_phone = os.environ.get("SIGNAL_PHONE")
    sig_key = os.environ.get("SIGNAL_API_KEY")

    channels = []
    if tg_token and tg_chat:
        channels.append(("Telegram", lambda p: telegram_alert.send_one(tg_token, tg_chat, p)))
    if sig_phone and sig_key:
        import signal_alert
        channels.append(("Signal", lambda p: signal_alert.send_one(sig_phone, sig_key, p)))

    if not channels:
        say("Alerty wylaczone (brak konfiguracji Telegram/Signal) - pomijam")
        return

    import scoring
    min_score = int(profile.get("min_score", 0) or 0)
    pending = digest.filter_for_profile(storage.get_unnotified_promotions(conn), profile)
    # Prog jakosci: alarmujemy tylko okazje z ocena >= min_score (0 = wszystko).
    pending = [p for p in pending if scoring.score_promo(p) >= min_score]
    sent = 0
    for promo in pending:
        results = [fn(promo) for _, fn in channels]
        if any(results):
            storage.mark_notified(conn, promo.id)
            sent += 1
    say(f"Alerty ({', '.join(n for n, _ in channels)}): wyslano {sent}/{len(pending)} (prog {min_score})")


def main() -> int:
    load_dotenv()
    profile = load_profile()
    new_promotions = run_pipeline()

    relevant = digest.filter_for_profile(new_promotions, profile)
    print()
    print(digest.format_digest(relevant))
    return 0


if __name__ == "__main__":
    sys.exit(main())
