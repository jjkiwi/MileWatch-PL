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
    # Realny prog dla lotow DALEKODYSTANSOWYCH (ekonomiczny): swietna cena na drugi koniec
    # swiata to zwykle 2000-3500 zl, nie <1500 zl. Lot longhaul ponizej tej ceny = perelka
    # NA SAMEJ CENIE (bez potrzeby slowa-hype). Dzieki temu np. Reunion 2750 zl sie lapie.
    "max_longhaul_pln": 3000,
    "max_longhaul_eur": 700,
    "max_longhaul_usd": 750,
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
# Dalekodystansowe kierunki - mega-tani lot tam jest naprawde wyjatkowy.
# Uwaga: dopasowanie po FRAGMENCIE tekstu, wiec unikamy krotkich tokenow, ktore wpadaja
# w polskie slowa (np. "oman" w "romantyczny", "lima" w "klimat", "mali" w "malina").
LONGHAUL = [
    # Azja
    "azja", "azji", "tajland", "thailand", "bangkok", "japoni", "japan", "tokio", "osaka",
    "chiny", "pekin", "szanghaj", "hongkong", "hong kong", "tajwan", "taiwan", "taipei",
    "korea", "seul", "seoul", "singapur", "bali", "indonezj", "dżakarta", "jakarta",
    "malediw", "maldives", "sri lanka", "wietnam", "hanoi", "sajgon", "filipiny", "manila",
    "kambodza", "kambodża", "cambodia", "laos", "birma", "myanmar", "nepal", "katmandu",
    "indie", "india", "delhi", "mumbai", "bombaj",
    # Bliski Wschod / Zatoka (dalekie loty tranzytowe)
    "emirat", "dubaj", "abu dhabi", "katar", "doha", "bahrajn", "maskat",
    # Ameryka Polnocna
    "usa", "stany", "nowy jork", "new york", "los angeles", "san francisco", "miami",
    "chicago", "boston", "seattle", "las vegas", "orlando", "houston", "dallas",
    "atlanta", "denver", "san diego", "waszyngton", "hawaje", "hawaii", "honolulu",
    "kanad", "toronto", "vancouver", "montreal", "calgary",
    # Ameryka Srodkowa i Karaiby
    "meksyk", "cancun", "karaib", "dominikan", "kuba", "hawana", "jamajka", "jamaica",
    "barbados", "bahamy", "bahamas", "portoryko", "aruba", "curacao", "kostaryka",
    "costa rica", "panama", "gwatemala", "belize",
    # Ameryka Poludniowa
    "brazyli", "rio de janeiro", "sao paulo", "argentyn", "buenos aires", "peru", "chile",
    "santiago", "kolumbia", "colombia", "bogota", "ekwador", "quito", "boliwia", "urugwaj",
    # Afryka i Ocean Indyjski
    "rpa", "kapsztad", "johannesburg", "durban", "kenia", "kenya", "tanzania", "zanzibar",
    "etiopia", "namibia", "botswana", "mozambik", "madagaskar", "madagascar", "seszele",
    "mauritius", "reunion", "réunion", "saint-denis", "senegal", "ghana", "nigeria",
    # Oceania / Pacyfik
    "australi", "sydney", "melbourne", "nowa zeland", "auckland", "fidzi", "fiji",
    "tahiti", "polinezja", "bora bora", "samoa", "tonga", "guam", "nowa kaledonia",
]

AIRLINES = [
    "Lufthansa", "LOT", "Swiss", "Austrian", "KLM", "Air France", "British Airways",
    "Qatar", "Emirates", "Etihad", "Turkish", "Singapore Airlines", "ITA Airways",
    "Finnair", "Iberia", "United", "American Airlines", "Delta",
]

# --- Filtr lotnisk wylotu (Faza 1) -------------------------------------------
# Perelki (tanie loty / bledy cenowe / biznes) maja sens, gdy wylot jest z Polski lub
# krajow oscienncych (Niemcy, Czechy, Slowacja, Austria, Litwa). Mozesz wylaczyc filtr
# ustawiajac FILTER_DEPARTURE = False, albo dopisac swoje lotniska do PREFERRED_DEP.
FILTER_DEPARTURE = True

PREFERRED_DEP = [
    # Polska (miasta + kody IATA)
    "warszawa", "warsaw", "warschau", "krakow", "kraków", "cracow", "krakau",
    "gdansk", "gdańsk", "danzig", "wroclaw", "wrocław", "breslau", "katowice", "kattowitz",
    "poznan", "poznań", "posen", "rzeszow", "rzeszów", "szczecin", "stettin",
    "bydgoszcz", "lublin", "lodz", "łódź", "modlin", "z polski", "aus polen", "from poland",
    "waw", "wmi", "krk", "gdn", "wro", "ktw", "poz", "rze", "szz", "bzg", "lcj",
    # Niemcy
    "berlin", "drezno", "dresden", "frankfurt", "monachium", "munchen", "münchen",
    "munich", "lipsk", "leipzig", "hamburg", "ber", "fra", "muc",
    # Czechy
    "praga", "prague", "prag", "ostrawa", "ostrava", "brno", "prg", "osr",
    # Slowacja
    "bratyslawa", "bratysława", "bratislava", "bts", "koszyce", "kosice",
    # Austria
    "wieden", "wiedeń", "wien", "vienna", "vie",
    # Litwa
    "wilno", "vilnius", "vno", "kowno", "kaunas",
]

# Wyrazne lotniska/miasta wylotu spoza regionu (czeste w feedach US/UK).
FARAWAY_DEP = [
    "san francisco", "los angeles", "new york", "newark", "miami", "chicago", "boston",
    "washington", "dallas", "seattle", "atlanta", "houston", "denver", "san diego",
    "portland", "sfo", "lax", "jfk", "ewr",
    "london", "londyn", "manchester", "edinburgh", "dublin",
    "madrid", "madryt", "barcelona", "lisbona", "lizbona", "lisbon", "lisboa",
    "paris", "paryz", "paryż", "amsterdam", "rzym", "mediolan", "milan", "milano",
    "bruksela", "brussels", "zurich", "zürich", "genewa", "geneva",
    "oslo", "sztokholm", "stockholm", "kopenhaga", "copenhagen", "helsinki",
]

_SEP_HINT = ("–", " - ", " to ", " do ", "from ", "ab ", "von ", "ex ")


def _departure(low: str):
    """Zwraca (relevant, preferowane_miasto_lub_None).

    relevant=False tylko gdy wykryto WYRAZNY wylot spoza regionu (miasto faraway przy
    separatorze trasy / "from"). Brak danych = zostawiamy (relevant=True).
    """
    pref = next((c for c in PREFERRED_DEP if c in low), None)
    if pref:
        return True, pref
    if any(s in low for s in _SEP_HINT) and any(c in low for c in FARAWAY_DEP):
        return False, None
    return True, None

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
    # Realny prog dla lotow dalekich: longhaul ponizej progu longhaul (>= progu mega) =
    # perelka na samej cenie, bez potrzeby slowa-hype.
    longhaul_cheap = is_longhaul and (
        (pln is not None and pln <= cfg["max_longhaul_pln"]) or
        (eur is not None and eur <= cfg["max_longhaul_eur"]) or
        (usd is not None and usd <= cfg["max_longhaul_usd"]))

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

    # 3) TANI LOT / mega okazja - tani lot dalekodystansowy (do progu longhaul, np. 3000 zl)
    #    albo oferta z hype. Celowo WASKI: nie alarmujemy o zwyklych tanich lotach do Europy.
    #    (longhaul_cheap obejmuje tez longhaul ponizej progu mega.) To NIE blad cenowy -> [TANI LOT].
    if typ is None and (longhaul_cheap or (is_hype and has_price)):
        typ = "great_deal"

    if typ is None:
        return None

    # Faza 1: priorytet wylotu. NIE odrzucamy ofert spoza regionu - zostawiamy je, ale
    # oznaczamy jako "Wylot zagraniczny". Takie perelki sa pokazywane (strona/GUI), tylko
    # nizej i BEZ alertu na Telegram/Signal (patrz digest.is_relevant). Wylot z Polski/krajow
    # oscienncych albo nieznany = pelny priorytet (alert).
    wylot_pref = None
    wylot_zagraniczny = False
    if FILTER_DEPARTURE:
        relevant, wylot_pref = _departure(low)
        wylot_zagraniczny = not relevant

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
    if wylot_zagraniczny:
        regiony.append("Wylot zagraniczny")

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
    if wylot_pref:
        parts.append(f"- wylot: {wylot_pref.capitalize()}")
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
