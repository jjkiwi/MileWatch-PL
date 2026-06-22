import logging
import sqlite3

import httpx

import storage
from models import Promotion

logger = logging.getLogger(__name__)

API_URL = "https://api.telegram.org/bot{token}/sendMessage"

# Tag kategorii doklejany na POCZATKU tytulu kazdej wiadomosci.
CATEGORY_TAGS = {
    "error_fare": "[‼️ BŁĄD CENOWY]",
    "business_class": "[💺 BIZNES KLASA]",
    "buy_miles": "[🛒 KUP MILE]",
    "partner_bonus": "[🤝 BONUS PARTNERA]",
    "mileage_bargain": "[🎯 OKAZJA MILOWA]",
    "card": "[💳 KARTA]",
    "other": "[✈️ MILES & MORE]",
}


def category_tag(typ: str) -> str:
    return CATEGORY_TAGS.get(typ, "[✈️ MILES & MORE]")


def format_message(promo: Promotion) -> str:
    tag = category_tag(promo.typ)
    bonus = f"\nBonus: +{promo.bonus_pct}%" if promo.bonus_pct else ""
    partner = f"\nPartner: {promo.partner}" if promo.partner else ""
    wazne_do = f"\nWazne do: {promo.wazne_do}" if promo.wazne_do else ""
    return (
        f"{tag} {promo.tytul}\n\n"
        f"{promo.streszczenie}"
        f"{bonus}{partner}{wazne_do}\n\n"
        f"Zrodlo ({promo.zrodlo_nazwa}): {promo.zrodlo_url}"
    )


def send_one(token: str, chat_id: str, promo: Promotion) -> bool:
    """Wysyla pojedynczy alert na Telegram (bez oznaczania w bazie). Zwraca True przy sukcesie."""
    url = API_URL.format(token=token)
    try:
        resp = httpx.post(
            url,
            json={"chat_id": chat_id, "text": format_message(promo),
                  "disable_web_page_preview": True},
            timeout=15,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("Telegram: nie udalo sie wyslac alertu '%s': %s", promo.tytul, e)
        return False
    return True


def send_alerts(
    conn: sqlite3.Connection, token: str, chat_id: str, promotions: list[Promotion]
) -> int:
    """Wysyla alert Telegram dla kazdej promocji i oznacza jako wyslana.

    Idempotentne: promocje juz oznaczone jako wyslane nie trafiaja tutaj (patrz
    storage.get_unnotified_promotions). Promocja, dla ktorej wyslanie sie nie powiedzie,
    nie jest oznaczana - zostanie ponowiona przy kolejnym uruchomieniu.
    """
    url = API_URL.format(token=token)
    sent = 0
    for promo in promotions:
        try:
            resp = httpx.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": format_message(promo),
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("Telegram: nie udalo sie wyslac alertu '%s': %s", promo.tytul, e)
            continue
        storage.mark_notified(conn, promo.id)
        sent += 1
    return sent
