"""Scoring okazji 0-100 (Faza 2) - "jak dobra to okazja".

Liczony w locie ze strukturalnych pol promocji (bez zapisu do bazy, bez migracji).
Uzywany do: gwiazdki w alercie, sortowania na stronie/GUI oraz progu alertu (min_score).

Skladniki:
  * baza zalezna od kategorii (blad cenowy > biznes > tani lot > promocje M&M > inne),
  * bonus % (dla promocji Miles & More),
  * dalekodystansowosc (perelka na drugi koniec swiata jest ciekawsza),
  * znana data waznosci / partner (drobny plus za konkret),
  * KARA za wylot spoza regionu (Polska + kraje oscienne) - mniej promujemy.
"""

from models import Promotion

BASE = {
    "error_fare": 80,       # jawny blad cenowy / mistake fare - perelka nad perelkami
    "business_class": 62,
    "great_deal": 50,       # tani lot / mega okazja
    "mileage_bargain": 42,
    "buy_miles": 35,
    "partner_bonus": 35,
    "card": 25,
    "other": 18,
}


def score_promo(promo: Promotion) -> int:
    """Zwraca ocene 0-100."""
    regiony = promo.regiony or []
    foreign = "Wylot zagraniczny" in regiony
    longhaul = "Dalekie loty" in regiony
    rekord = "Rekord cenowy" in regiony
    zloty = "Zloty termin" in regiony
    bonus = promo.bonus_pct or 0

    s = float(BASE.get(promo.typ, 18))

    # Zloty termin (okno urlopowe uzytkownika) - najwyzszy priorytet: mocno podbijamy,
    # zeby taka oferta wskoczyla na gore listy i przebila prog alertu (min_score).
    if zloty:
        s += 30

    # Cena rekordowo niska dla kierunku (baseline, Faza 3) - mocny sygnal.
    if rekord:
        s += 15

    # Bonus % (promocje Miles & More): +35 pkt przy 100% bonusu.
    if bonus:
        s += min(bonus, 150) * 0.35

    # Perelka dalekodystansowa - ciekawsza.
    if longhaul and promo.typ in ("error_fare", "great_deal", "business_class"):
        s += 10

    # Konkret = wieksze zaufanie do oferty.
    if promo.wazne_do:
        s += 3
    if promo.partner:
        s += 3

    # Wylot spoza regionu - mocno w dol (mniej promujemy).
    if foreign:
        s -= 25

    return max(0, min(100, round(s)))


def stars(score: int) -> str:
    """Krotki wskaznik gwiazdkowy do alertu, np. '★★★★☆'."""
    full = round(score / 20)
    return "★" * full + "☆" * (5 - full)
