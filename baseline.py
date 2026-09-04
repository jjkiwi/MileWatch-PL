"""Baseline cen tras (Faza 3) - uczy sie rozkladu cen i ocenia, JAK BARDZO promocyjna jest oferta.

Dla kazdej perelki z wykrywalna cena i kierunkiem zapisuje obserwacje do tabeli price_history,
a przy ocenie porownuje biezaca cene z HISTORIA tego kierunku - nie binarnie, lecz PERCENTYLOWO:
  * najtansze ~10% (albo nowe minimum) -> "Rekord cenowy"   (duzy bonus w scoringu),
  * najtansze ~25%                      -> "Dobra cena"      (sredni bonus).
Dzieki temu silnik z czasem coraz lepiej odroznia "naprawde promocyjne" od "typowej ceny trasy"
(np. "150 zl do Szwecji" przestaje byc perelka, gdy to normalna cena, a 90 zl - juz tak).

Cold start: dopoki nie ma min. kilku obserwacji danego kierunku, nie oznaczamy niczego
(zeby na poczatku nie flagowac wszystkiego). System uczy sie z czasem.
"""

import re
import sqlite3
from datetime import datetime, timedelta, timezone

import deals  # reuzywamy wyrazenia cenowe i _cheapest

MIN_OBS = 3          # minimalna liczba obserwacji, zanim zaczniemy oceniac cene
HISTORY_DAYS = 365   # okno historii do porownan
P_RECORD = 0.10      # cena <= 10. percentyla historii = "Rekord cenowy"
P_GOOD = 0.25        # cena <= 25. percentyla historii = "Dobra cena"

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
    # dalekie - uzupelnienie (zsynchronizowane z rozszerzona lista deals.LONGHAUL)
    "reunion", "réunion", "madagask", "kenia", "tanzani", "korea", "tajwan", "taiwan",
    "indie", "kolumbi", "ekwador", "boliwi", "panama", "kostaryka", "jamajk", "bahamy",
    "fidzi", "tahiti", "hawaje", "wenezuel", "nepal", "kambodz", "laos", "namibi",
    "mozambik", "senegal", "ghana",
    # bliskie/europa (rdzenie lapiace odmiane: "szwecj" -> Szwecja/Szwecji/Szwecje)
    "szwecj", "norwegi", "finlandi", "dania", "islandi", "hiszpani", "portugali",
    "wloch", "włoch", "grecj", "chorwacj", "cypr", "malta", "albani", "turcj", "maroko",
    "egipt", "tunezj", "izrael", "gruzj", "armeni", "wielka brytani", "londyn", "irlandi",
    "francj", "paryz", "niderlandy", "amsterdam", "belgi", "niemcy", "austri", "szwajcari",
    "mader", "teneryf", "kanaryjsk", "azory", "lizbon", "barcelon", "rzym", "stambu",
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
    # Dopasowanie po granicy slowa (jak w regionach), zeby "peru" nie lapalo "peruka" itp.
    found = [p for p in PLACES if re.search(r"\b" + re.escape(p), low)]
    return found[-1] if found else None   # ostatnie dopasowanie - czesto cel podrozy


def _quantile(sorted_vals: list, q: float) -> float:
    """Percentyl (interpolowany) z posortowanej listy. q w [0,1]."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def assess(conn: sqlite3.Connection, promo):
    """Ocenia, jak promocyjna jest cena wzgledem historii kierunku (percentylowo).

    Mutuje promo (regiony += "Rekord cenowy" / "Dobra cena", notka w streszczeniu).
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
    prices = sorted(r[0] for r in rows)

    if len(prices) >= MIN_OBS:
        prev_min = prices[0]
        median = round(_quantile(prices, 0.5))
        p_rec = _quantile(prices, P_RECORD)
        p_good = _quantile(prices, P_GOOD)
        tag = note = None
        if amount < prev_min:
            tag = "Rekord cenowy"
            note = f"Najnizsza cena ({amount} {currency}) dla kierunku '{place}' od co najmniej roku"
        elif amount <= p_rec:
            tag = "Rekord cenowy"
            note = (f"Cena {amount} {currency} w najtanszych ~10% ofert dla '{place}' "
                    f"(mediana ~{median} {currency})")
        elif amount <= p_good:
            tag = "Dobra cena"
            note = (f"Cena {amount} {currency} w najtanszych ~25% ofert dla '{place}' "
                    f"(mediana ~{median} {currency})")
        if tag:
            if tag not in promo.regiony:
                promo.regiony.append(tag)
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
