"""Baseline cen tras (Faza 3) - uczy sie typowych cen i wykrywa "naprawde tanio".

Dla kazdej perelki z wykrywalna cena i kierunkiem zapisuje obserwacje do tabeli
price_history, a przy ocenie porownuje biezaca cene z historia tego kierunku. Jesli cena
jest rekordowo niska (albo mocno ponizej typowej), oznacza promocje "Rekord cenowy"
(co podbija scoring) i dopisuje notke do streszczenia. Dzieki temu "150 zl do Szwecji"
przestaje byc perelka, gdy okaze sie typowa cena tej trasy.

Cold start: dopoki nie ma min. kilku obserwacji danego kierunku, nie oznaczamy rekordow
(zeby na poczatku nie flagowac wszystkiego). System uczy sie z czasem.
"""

import sqlite3
from datetime import datetime, timedelta, timezone

import deals  # reuzywamy wyrazenia cenowe i _cheapest

MIN_OBS = 3          # minimalna liczba obserwacji, zanim zaczniemy oznaczac rekordy
HISTORY_DAYS = 365   # okno historii do porownan
BELOW_MEDIAN = 0.70  # cena <= 70% mediany = rekord (mocno ponizej typowej)

# Znane kierunki/miejsca (do klucza trasy). Ostatnie dopasowanie w tekscie traktujemy
# jako cel podrozy ("Origin - Cel"). Lista celowo szeroka.
PLACES = [
    # dalekie
    "bangkok", "tajland", "japoni", "tokio", "azja", "singapur", "bali", "indonezj",
    "malediw", "sri lanka", "wietnam", "filipiny", "chiny", "pekin", "hongkong",
    "nowy jork", "new york", "los angeles", "san francisco", "miami", "usa", "kanad",
    "toronto", "meksyk", "karaib", "dominikan", "kuba", "brazyli", "argentyn", "peru",
    "chile", "australi", "nowa zeland", "rpa", "kapsztad", "dubaj", "abu dhabi", "katar",
    "doha", "seszele", "mauritius", "zanzibar", "maldives", "dalian",
    # bliskie/europa
    "szwecja", "norwegia", "finlandia", "dania", "islandia", "hiszpani", "portugali",
    "wlochy", "grecja", "chorwacj", "cypr", "malta", "albani", "turcj", "maroko",
    "egipt", "tunezj", "izrael", "gruzj", "armeni", "wielka brytani", "londyn", "irlandi",
    "francj", "paryz", "niderlandy", "amsterdam", "belgi", "niemcy", "austri", "szwajcari",
]


def _cutoff_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _price(text: str):
    pln = deals._cheapest(text, [deals.PLN_RE])
    if pln is not None:
        return "PLN", pln
    eur = deals._cheapest(text, [deals.EUR_RE_A, deals.EUR_RE_B])
    if eur is not None:
        return "EUR", eur
    usd = deals._cheapest(text, [deals.USD_RE_A, deals.USD_RE_B])
    if usd is not None:
        return "USD", usd
    return None, None


def _place(low: str):
    found = [p for p in PLACES if p in low]
    return found[-1] if found else None   # ostatnie dopasowanie - czesto cel podrozy


def assess(conn: sqlite3.Connection, promo):
    """Ocenia, czy cena promocji jest rekordowo niska dla jej kierunku.

    Jesli tak - mutuje promo (regiony += "Rekord cenowy", notka w streszczeniu).
    Zwraca obserwacje (route, currency, amount) do pozniejszego zapisu, albo None.
    """
    blob = f"{promo.tytul} {promo.streszczenie}"
    currency, amount = _price(blob)
    place = _place(blob.lower())
    if not place or amount is None:
        return None

    rows = conn.execute(
        "SELECT amount FROM price_history WHERE route=? AND currency=? AND ts>=?",
        (place, currency, _cutoff_iso(HISTORY_DAYS)),
    ).fetchall()
    prices = [r[0] for r in rows]

    if len(prices) >= MIN_OBS:
        prev_min = min(prices)
        srt = sorted(prices)
        median = srt[len(srt) // 2]
        note = None
        if amount < prev_min:
            note = f"Najnizsza cena ({amount} {currency}) dla kierunku '{place}' od co najmniej roku"
        elif amount <= median * BELOW_MEDIAN:
            note = (f"Cena {amount} {currency} mocno ponizej typowej (~{median} {currency}) "
                    f"dla kierunku '{place}'")
        if note:
            if "Rekord cenowy" not in promo.regiony:
                promo.regiony.append("Rekord cenowy")
            promo.streszczenie = (promo.streszczenie.rstrip(". ") + ". " + note + ".").strip()

    return (place, currency, amount)


def record(conn: sqlite3.Connection, obs) -> None:
    """Zapisuje obserwacje ceny do historii (wywolaj po udanym zapisie promocji)."""
    if not obs:
        return
    route, currency, amount = obs
    conn.execute(
        "INSERT INTO price_history (route, currency, amount, ts) VALUES (?, ?, ?, ?)",
        (route, currency, amount, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
