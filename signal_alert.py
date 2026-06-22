"""Alerty Signal przez CallMeBot - darmowy relay, bez wlasnego serwera.

CallMeBot udostepnia darmowe API do wysylania wiadomosci na Signal prostym zadaniem HTTP GET.
Rejestracja (jednorazowo, za darmo):
  1. Dodaj numer CallMeBot do kontaktow Signal: +34 644 51 95 23
  2. Wyslij do niego wiadomosc: "I allow callmebot to send me messages"
  3. W odpowiedzi dostaniesz swoj API key (apikey).
  4. Wpisz w .env: SIGNAL_PHONE=+48... (Twoj numer) oraz SIGNAL_API_KEY=...

Uwaga: wiadomosci przechodza przez zewnetrzny serwis CallMeBot.
"""

import logging
import urllib.parse

import httpx

from models import Promotion
from telegram_alert import format_message

logger = logging.getLogger(__name__)

API_URL = "https://signal.callmebot.com/signal/send.php"


def send_one(phone: str, apikey: str, promo: Promotion) -> bool:
    """Wysyla pojedynczy alert na Signal. Zwraca True przy sukcesie."""
    params = {
        "phone": phone,
        "apikey": apikey,
        "text": format_message(promo),
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    try:
        resp = httpx.get(url, timeout=20)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("Signal: nie udalo sie wyslac alertu '%s': %s", promo.tytul, e)
        return False
    return True
