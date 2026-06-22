"""Wykrywanie TOP perelek lotniczych - selektywnie, bez LLM.

Dwie kategorie (poza promocjami Miles & More z extract.py):
  * error_fare      - bledy cenowe / mistake fares ALBO mega-tanie loty dalekodystansowe,
  * business_class  - bardzo tanie promocyjne loty w klasie biznes.

Filtr jest CELOWO waski (user chce tylko "serio duze promocje lub bledy cenowe"),
zeby nie zasypywac alertami o zwyklych tanich lotach do Europy.

Progi cenowe mozna dostroic ponizej (DEFAULT_*).
"""

import re

from models import Promotion

# --- Progi (mozesz dostroic) -------------------------------------------------
DEFAULT = {
    # Mega-tani lot dalekodystansowy (ekonomiczny) ponizej tej ceny = perelka.
    "max_mega_pln": 1500,
    "max_mega_eur": 350,
    "max_mega_usd": 400,
    # Bardzo tani lot w klasie biznes ponizej tej ceny = perelka.
    "max_business_pln": 4000,
    "max_business_eur": 900,
    "max_business_usd": 1000,
}

# --- Sygnaly -----------------------------------------------------------------

# JAWNE bledy cenowe / mistake fare - tylko to daje tag [BLAD CENOWY]. Naprawde rzadkie.
ERROR_SIGNALS = [
    "error fare", "mistake fare", "blad cenowy", "błąd cenowy", "blad w cenie",
    "błąd w cenie", "pomylka cenowa", "pomyłka cenowa", "cena z bledu", "cena z błędu",
    "fehlerfare", "fehlbuchung", "fehlpreis", "price mistake",
]

# Slowa-hype (marketing serwisow). NIE oznaczaja bledu cenowego - tylko "tani lot"/okazje.
# Wczesniej myslnie wpadaly do bledow cenowych (np. zwykla Szwecja za 150 zl z "rekordowo tanio").
HYPE_SIGNALS = [
    "najtaniej w historii", "rekordowo tanio", "rekordowa cena", "bezprecedensowa cena",
    "mega okazja", "mega promocja", "hit cenowy", "super cena", "wyjatkowa okazja",
    "okazja", "promocja dnia", "last minute hit",
]

BUSINESS_SIGNALS = [
    "business class", "klasa biznes", "klasie biznes", "klasy biznes", "biznes klasa",
    "klasą biznes", "business-class", "lie-flat", "lie flat", "fotele biznes",
]

# Dalekodystansowe kierunki - mega-tani lot tam jest naprawde wyjatkowy.
LONGHAUL = [
    "azja", "azji", "tajland", "bangkok", "japoni", "tokio", "chiny", "pekin",
    "singapur", "bali", "indonezj", "malediw", "sri lanka", "wietnam", "filipiny",
    "usa", "stany", "nowy jork", "new york", "los angeles", "miami", "kanad", "toronto",
    "meksyk", "karaib", "dominikan", "kuba", "brazyli", "argentyn", "peru", "chile",
    "australi", "nowa zeland", "rpa", "kapsztad", "emirat", "dubaj", "abu dhabi",
    "katar", "doha", "seszele", "mauritius", "zanzibar", "japan", "thailand", "maldives",
]

AIRLINES = [
    "Lufthansa", "LOT", "Swiss", "Austrian", "KLM", "Air France", "British Airways",
    "Qatar", "Emirates", "Etihad", "Turkish", "Singapore Airlines", "ITA Airways",
    "Finnair", "Iberia", "United", "American Airlines", "Delta",
]

# --- Ceny --------------------------------------------------------------------

PLN_RE = re.compile(r"(\d[\d\s. ]{0,8}\d|\d)\s*(?:z[lł]|pln)", re.IGNORECASE)
EUR_RE_A = re.compile(r"(?:€|eur)\s*(\d[\d\s. ]{0,8}\d|\d)", re.IGNORECASE)
EUR_RE_B = re.compile(r"(\d[\d\s. ]{0,8}\d|\d)\s*(?:€|eur)", re.IGNORECASE)


def _to_int(raw: str) -> int | None:
    digits = re.sub(r"[^\d]", "", raw)  # usuwa spacje, kropki, nbsp jako separatory tysiecy
    if not digits:
        return None
    val = int(digits)
    return val if 50 <= val <= 50000 else None


USD_RE_A = re.compile(r"(?:\$|usd)\s*(\d[\d\s.,]{0,8}\d|\d)", re.IGNORECASE)
USD_RE_B = re.compile(r"(\d[\d\s.,]{0,8}\d|\d)\s*usd", re.IGNORECASE)


def _cheapest(text: str, regexes) -> int | None:
    vals = []
    for rx in regexes:
        for m in rx.finditer(text):
            v = _to_int(m.group(1))
            if v is not None:
                vals.append(v)
    return min(vals) if vals else None


def _contains_any(low: str, signals) -> bool:
    return any(s in low for s in signals)


def _airline(text: str) -> str | None:
    for a in AIRLINES:
        if re.search(r"\b" + re.escape(a) + r"\b", text, re.IGNORECASE):
            return a
    return None


def _first_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if len(line) >= 8:
            return line[:160]
    return text.strip()[:160]


def detect_deal(raw_item: dict, cfg: dict | None = None) -> Promotion | None:
    """Zwraca Promotion (typ error_fare/business_class) albo None. Najwyzej jedna na item."""
    cfg = {**DEFAULT, **(cfg or {})}
    text = raw_item.get("tekst", "")
    if not text or len(text.strip()) < 8:
        return None
    low = text.lower()

    pln = _cheapest(text, [PLN_RE])
    eur = _cheapest(text, [EUR_RE_A, EUR_RE_B])
    usd = _cheapest(text, [USD_RE_A, USD_RE_B])
    is_error = _contains_any(low, ERROR_SIGNALS)   # TYLKO jawny blad cenowy
    is_hype = _contains_any(low, HYPE_SIGNALS)     # marketing: "rekordowo tanio" itp.
    is_business = _contains_any(low, BUSINESS_SIGNALS)
    is_longhaul = _contains_any(low, LONGHAUL)
    has_price = pln is not None or eur is not None or usd is not None
    mega = ((pln is not None and pln <= cfg["max_mega_pln"]) or
            (eur is not None and eur <= cfg["max_mega_eur"]) or
            (usd is not None and usd <= cfg["max_mega_usd"]))

    typ = None

    # 1) Tania biznes klasa (priorytet - najbardziej konkretna kategoria).
    if is_business:
        cheap_biz = ((pln is not None and pln <= cfg["max_business_pln"]) or
                     (eur is not None and eur <= cfg["max_business_eur"]) or
                     (usd is not None and usd <= cfg["max_business_usd"]))
        if cheap_biz or is_error:
            typ = "business_class"

    # 2) BLAD CENOWY - tylko gdy tekst JAWNIE mowi o bledzie/mistake fare.
    if typ is None and is_error:
        typ = "error_fare"

    # 3) TANI LOT / mega okazja - bardzo tani lot dalekodystansowy albo oferta z hype.
    #    To NIE jest blad cenowy, wiec dostanie tag [TANI LOT], nie [BLAD CENOWY].
    if typ is None and ((is_longhaul and mega) or (is_hype and has_price)):
        typ = "great_deal"

    if typ is None:
        return None

    # Cena do streszczenia (pierwsza dostepna waluta)
    if pln is not None:
        cena_txt = f"{pln} zl"
    elif eur is not None:
        cena_txt = f"{eur} EUR"
    elif usd is not None:
        cena_txt = f"{usd} USD"
    else:
        cena_txt = None

    tytul = _first_line(text)
    tl = tytul.lower()
    if any(m in tl for m in ("archive", "archiwum", "kategoria", "category",
                             "- insideflyer", "tag:", "feed", "strona ")):
        return None  # smiec ze strony-listy/archiwum, nie oferta

    partner = _airline(text)
    regiony = []
    if is_longhaul:
        regiony.append("Dalekie loty")

    labels = {
        "error_fare": "Blad cenowy (mistake fare)",
        "business_class": "Tania klasa biznes",
        "great_deal": "Tani lot / mega okazja",
    }
    parts = [labels.get(typ, "Okazja lotnicza")]
    if cena_txt:
        parts.append(f"od {cena_txt}")
    if partner:
        parts.append(f"({partner})")
    streszczenie = " ".join(parts) + "."

    return Promotion(
        id="",
        tytul=tytul,
        typ=typ,
        bonus_pct=None,
        partner=partner,
        wazne_do=None,
        regiony=regiony,
        trasy=[],
        zrodlo_url=raw_item.get("zrodlo_url", ""),
        zrodlo_nazwa=raw_item.get("zrodlo_nazwa", ""),
        streszczenie=streszczenie,
    )
