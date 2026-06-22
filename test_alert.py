"""Wysyla wiadomosc testowa na skonfigurowane kanaly (Telegram/Signal).

Uzycie:  python test_alert.py
Sprawdza, czy alerty sa dobrze ustawione w .env.
"""

import os
import urllib.parse

import httpx


def load_env(path=".env"):
    """Wczytuje .env bez zaleznosci zewnetrznych (gdyby brakowalo python-dotenv)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


load_env()

TEXT = "MileWatch PL: wiadomosc testowa - alerty dzialaja."


def main() -> int:
    sent = False

    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID")
    if tg_token and tg_chat:
        try:
            r = httpx.post(f"https://api.telegram.org/bot{tg_token}/sendMessage",
                           json={"chat_id": tg_chat, "text": TEXT}, timeout=15)
            r.raise_for_status()
            print("Telegram: OK")
            sent = True
        except httpx.HTTPError as e:
            print(f"Telegram: BLAD - {e}")

    sig_phone = os.environ.get("SIGNAL_PHONE")
    sig_key = os.environ.get("SIGNAL_API_KEY")
    if sig_phone and sig_key:
        params = urllib.parse.urlencode({"phone": sig_phone, "apikey": sig_key, "text": TEXT})
        try:
            r = httpx.get(f"https://signal.callmebot.com/signal/send.php?{params}", timeout=20)
            r.raise_for_status()
            print("Signal: OK")
            sent = True
        except httpx.HTTPError as e:
            print(f"Signal: BLAD - {e}")

    if not sent:
        print("Brak skonfigurowanych kanalow (uzupelnij .env: TELEGRAM_* lub SIGNAL_*).")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
