"""Darmowa ekstrakcja promocji Miles & More z surowego tekstu - bez LLM, bez API.

Dziala w 100% lokalnie i za darmo: wykrywa promocje przy pomocy slow kluczowych i wyrazen
regularnych, a streszczenie buduje WLASNYMI SLOWAMI ze strukturalnych pol (nie kopiuje tresci
zrodla). Rozpoznaje sygnaly po polsku, niemiecku i angielsku - zrodla o Miles & More sa
czesto niemieckie (InsideFlyer.de) lub angielskie.
"""

import re
from datetime import datetime

from models import Promotion

# --- Slowniki sygnalow (male litery) -----------------------------------------

# Promocja musi byc powiazana z Miles & More / programem mil. Lista celowo precyzyjna,
# zeby na szerokich feedach (np. fly4free) nie lapac przypadkowych wpisow.
MILES_SIGNALS = [
    "miles & more", "miles and more", "milesandmore", "miles&more", "miles + more",
    "lufthansa", "star alliance", "swiss", "austrian airlines", "senator",
    "meilen",                      # niem. "mile"
    "mile lotnicze", "mil lotniczych", "okazje milowe", "okazja milowa",
]

# Sygnaly, ze chodzi o promocje/okazje (PL + DE + EN).
PROMO_SIGNALS = [
    # PL
    "promocj", "okazj", "rabat", "znizk", "zniżk", "oferta", "ofert", "taniej",
    "kup mile", "mnoznik", "mnożnik", "bonus", "%",
    # DE
    "aktion", "angebot", "rabatt", "sparen", "prozent", "gratis", "deal",
    "schnäppchen", "schnaeppchen", "meilen kaufen", "meilen-aktion",
    # EN
    "offer", "discount", "promotion", "sale", "save", "earn", "double", "triple",
    "buy miles", "limited",
]

# Mapowanie typu promocji na sygnaly (kolejnosc = priorytet).
TYPE_SIGNALS = {
    "buy_miles": ["kup mile", "buy miles", "buy bonus miles", "meilen kaufen",
                  "zakup mil", "dokup mile", "buy & gift", "meilenkauf"],
    "partner_bonus": ["transfer bonus", "partner", "hotel", "marriott", "hilton",
                      "accor", "hertz", "avis", "sixt", "kreditkarte", "credit card",
                      "earn bonus", "transferbonus", "punktetransfer"],
    "mileage_bargain": ["mileage bargain", "okazja milowa", "okazje milowe",
                        "meilenschnäppchen", "meilen-schnäppchen", "award", "nagrod",
                        "redemption", "wymiana mil", "praemienflug", "prämienflug"],
    "card": ["karta kredytowa", "credit card", "kreditkarte", "karty kredytowej",
             "card bonus", "miles & more card"],
}

# Znani partnerzy do wyciagniecia z tekstu.
KNOWN_PARTNERS = [
    "Lufthansa", "LOT", "Swiss", "Austrian", "Brussels Airlines", "Eurowings",
    "United", "Air Canada", "Singapore Airlines", "Marriott", "Hilton", "Accor",
    "Radisson", "Hertz", "Avis", "Sixt", "Europcar", "Star Alliance",
    "Diners Club", "Mastercard", "Visa",
]

# Regiony.
REGION_SIGNALS = {
    "Polska": ["polska", "polski", "warszawa", "krakow", "kraków", "pln", "zlot", "polen"],
    "Europa": ["europa", "europ", "niemcy", "frankfurt", "monachium", "münchen", "deutschland"],
    "Ameryka Polnocna": ["usa", "stany", "ameryka", "kanada", "new york", "nowy jork"],
    "Azja": ["azja", "azji", "singapur", "tajland", "japoni", "chiny", "asien"],
}

# --- Wyrazenia regularne ------------------------------------------------------

# "+50%", "50 %", "do 100%", "bis zu 100%", "up to 75%", "bonus 75%"
BONUS_RE = re.compile(r"(?:\+|do\s+|bis\s+zu\s+|up\s+to\s+|bonus\s+|az\s+|aż\s+)?(\d{1,3})\s*%")

# Daty waznosci
DATE_PATTERNS = [
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),                 # 2026-07-31
    re.compile(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})"),    # 31.07.2026
]
MONTHS_PL = {
    "stycznia": 1, "lutego": 2, "marca": 3, "kwietnia": 4, "maja": 5,
    "czerwca": 6, "lipca": 7, "sierpnia": 8, "wrzesnia": 9, "września": 9,
    "pazdziernika": 10, "października": 10, "listopada": 11, "grudnia": 12,
}
MONTHS_EN = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}
MONTHS_DE = {
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5, "juni": 6,
    "juli": 7, "august": 8, "september": 9, "oktober": 10, "november": 11, "dezember": 12,
}
_ALL_MONTHS = {**MONTHS_PL, **MONTHS_EN, **MONTHS_DE}
DATE_WORD_RE = re.compile(
    r"(\d{1,2})\.?\s+(" + "|".join(re.escape(m) for m in _ALL_MONTHS) + r")\s+(\d{4})",
    re.IGNORECASE,
)

TYPE_LABELS_PL = {
    "buy_miles": "kup mile",
    "partner_bonus": "bonus partnerski",
    "mileage_bargain": "okazja milowa",
    "card": "promocja karty",
    "other": "promocja Miles & More",
}


def _contains_any(text_low: str, signals: list[str]) -> bool:
    return any(s in text_low for s in signals)


def _detect_type(text_low: str) -> str:
    for typ, signals in TYPE_SIGNALS.items():
        if _contains_any(text_low, signals):
            return typ
    return "other"


def _extract_bonus(text: str) -> int | None:
    best = None
    for m in BONUS_RE.finditer(text):
        val = int(m.group(1))
        if 0 < val <= 300:
            best = val if best is None else max(best, val)
    return best


def _extract_partner(text: str) -> str | None:
    for partner in KNOWN_PARTNERS:
        if re.search(r"\b" + re.escape(partner) + r"\b", text, re.IGNORECASE):
            return partner
    return None


def _extract_regions(text_low: str) -> list[str]:
    found = []
    for region, signals in REGION_SIGNALS.items():
        if _contains_any(text_low, signals):
            found.append(region)
    return found


def _extract_valid_until(text: str) -> str | None:
    """Zwraca najpozniejsza sensowna date jako ISO 'YYYY-MM-DD' lub None."""
    candidates: list[str] = []
    for m in DATE_PATTERNS[0].finditer(text):
        candidates.append(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")
    for m in DATE_PATTERNS[1].finditer(text):
        d, mo, y = m.group(1), m.group(2), m.group(3)
        candidates.append(f"{y}-{int(mo):02d}-{int(d):02d}")
    for m in DATE_WORD_RE.finditer(text):
        d, month_name, y = m.group(1), m.group(2).lower(), m.group(3)
        mo = _ALL_MONTHS[month_name]
        candidates.append(f"{y}-{mo:02d}-{int(d):02d}")

    valid = []
    for c in candidates:
        try:
            dt = datetime.strptime(c, "%Y-%m-%d")
            if 2024 <= dt.year <= 2030:
                valid.append(c)
        except ValueError:
            continue
    return max(valid) if valid else None


def _first_meaningful_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if len(line) >= 8:
            return line[:160]
    return text.strip()[:160]


def _build_summary(typ: str, bonus: int | None, partner: str | None,
                   wazne_do: str | None) -> str:
    """Buduje krotkie streszczenie WLASNYMI SLOWAMI ze strukturalnych pol."""
    parts = [TYPE_LABELS_PL.get(typ, "promocja Miles & More").capitalize()]
    if bonus:
        parts.append(f"z bonusem do {bonus}%")
    if partner:
        parts.append(f"od partnera {partner}")
    summary = " ".join(parts) + "."
    if wazne_do:
        summary += f" Wazne do {wazne_do}."
    return summary


def extract_from_item(raw_item: dict) -> list[Promotion]:
    """Z surowego itemu (tekst + zrodlo) zwraca 0-1 promocji.

    Jesli tekst nie wyglada na promocje Miles & More, zwraca pusta liste.
    """
    text = raw_item.get("tekst", "")
    if not text or len(text.strip()) < 8:
        return []

    text_low = text.lower()
    if not _contains_any(text_low, MILES_SIGNALS):
        return []
    if not _contains_any(text_low, PROMO_SIGNALS):
        return []

    typ = _detect_type(text_low)
    bonus = _extract_bonus(text)
    partner = _extract_partner(text)
    regiony = _extract_regions(text_low)
    wazne_do = _extract_valid_until(text)

    # Odsiewanie newsow: wpis bez konkretnego TYPU promocji (other), bez bonusu % i bez daty
    # waznosci to prawie zawsze artykul informacyjny ("Lufthansa zwieksza udzialy do 90 Prozent",
    # "dynamic pricing") albo tytul strony - nie realna promocja. Pomijamy.
    if typ == "other" and bonus is None and wazne_do is None:
        return []

    tytul = _first_meaningful_line(text)

    # Odsiewanie smieci ze stron-list/archiwow (scraping strony kategorii oddaje jako "tytul"
    # naglowek strony, np. "Miles & More Archive - InsideFlyer DE"), to nie jest oferta.
    tl = tytul.lower()
    if any(m in tl for m in ("archive", "archiwum", "kategoria", "category",
                             "- insideflyer", "tag:", "feed", "strona ")):
        return []
    streszczenie = _build_summary(typ, bonus, partner, wazne_do)

    return [
        Promotion(
            id="",
            tytul=tytul,
            typ=typ,
            bonus_pct=bonus,
            partner=partner,
            wazne_do=wazne_do,
            regiony=regiony,
            trasy=[],
            zrodlo_url=raw_item.get("zrodlo_url", ""),
            zrodlo_nazwa=raw_item.get("zrodlo_nazwa", ""),
            streszczenie=streszczenie,
        )
    ]
