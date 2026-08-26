"""Zlote terminy - okna urlopowe uzytkownika.

Uzytkownik podaje w config.yaml okresy (od-do), w ktorych ma urlop i moze gdzies poleciec.
Termin to OKRES, nie sztywna data wylotu. Jesli w tekscie oferty wykryjemy TERMIN PODROZY
(pojedyncza data, zakres dat albo miesiac/miesiace), ktory zachodzi na ktorekolwiek okno
urlopowe, oznaczamy promocje tagiem "Zloty termin" - taka oferta jest zawsze alertowana,
mocno podbijana w scoringu i wskakuje na gore listy.

Ograniczenie (swiadome): dziala tylko gdy termin podrozy jest w tresci. Krotkie zajawki RSS
czesto go nie zawieraja - wtedy pomaga profile.pelna_tresc: true (dociaga pelny artykul).
Filozofia: preferujemy RECALL (lepiej zaalarmowac o cos z urlopu niz przegapic), wiec
dopasowanie jest celowo hojne, ale pojedyncze daty licza sie tylko przy slowie o podrozy
(zeby nie mylic daty waznosci promocji z terminem lotu).
"""

import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta

from extract import _ALL_MONTHS as _EXTRACT_MONTHS

logger = logging.getLogger(__name__)

TAG = "Zloty termin"

# Nazwy miesiecy PL w kilku przypadkach (mianownik "wrzesien", miejscownik "we wrzesniu"),
# do tego formy z extract.py (dopelniacz PL "wrzesnia" oraz EN/DE). Warianty z/bez polskich znakow.
_EXTRA_PL = {
    # mianownik
    "styczen": 1, "styczeń": 1, "luty": 2, "marzec": 3, "kwiecien": 4, "kwiecień": 4,
    "maj": 5, "czerwiec": 6, "lipiec": 7, "sierpien": 8, "sierpień": 8,
    "wrzesien": 9, "wrzesień": 9, "pazdziernik": 10, "październik": 10,
    "listopad": 11, "grudzien": 12, "grudzień": 12,
    # miejscownik ("w styczniu", "we wrzesniu"...)
    "styczniu": 1, "lutym": 2, "marcu": 3, "kwietniu": 4, "maju": 5, "czerwcu": 6,
    "lipcu": 7, "sierpniu": 8, "wrzesniu": 9, "wrześniu": 9,
    "pazdzierniku": 10, "październiku": 10, "listopadzie": 11, "grudniu": 12,
}
MONTHS = {**_EXTRACT_MONTHS, **_EXTRA_PL}
_MONTH_ALT = "|".join(sorted((re.escape(m) for m in MONTHS), key=len, reverse=True))

# Separator zakresu: "-", "–", "—", "do", "bis", "to", ... (z opcjonalnymi spacjami).
_SEP = r"(?:\s*(?:-|–|—|−|do|bis|to|und|and)\s*)"

# Slowa sygnalizujace, ze data/miesiac to TERMIN PODROZY (a nie np. data waznosci promocji).
TRAVEL_KW = [
    "termin", "podróż", "podroz", "wylot", "wyloty", "lot", "loty", "lataj", "wyjazd",
    "wyjedz", "urlop", "reise", "reisezeitraum", "zeitraum", "reisen", "travel", "fly",
    "flight", "flights", "available", "verfügbar", "verfugbar",
]

R_ISO_RANGE = re.compile(r"(\d{4}-\d{2}-\d{2})" + _SEP + r"(\d{4}-\d{2}-\d{2})")
R_DMY_RANGE = re.compile(
    r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})" + _SEP + r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})"
)
# Pierwsza data bez roku: "01.09 - 15.12.2026"
R_DM_RANGE = re.compile(
    r"(\d{1,2})[.\-/](\d{1,2})\.?" + _SEP + r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})"
)
# Zakres dni w obrebie miesiaca: "od 10 do 20 sierpnia 2026", "10-20 sierpnia"
R_DAYRANGE_MONTH = re.compile(
    r"(\d{1,2})\.?" + _SEP + r"(\d{1,2})\.?\s+(" + _MONTH_ALT + r")\s*(\d{4})?",
    re.IGNORECASE,
)
# Zakres miesiecy: "wrzesien - grudzien 2026", "September bis Dezember 2026"
R_MONTH_RANGE = re.compile(
    r"(" + _MONTH_ALT + r")\s*(\d{4})?" + _SEP + r"(" + _MONTH_ALT + r")\s*(\d{4})?",
    re.IGNORECASE,
)
# Pojedyncze "31 lipca 2026"
R_DAY_MONTH = re.compile(r"(\d{1,2})\.?\s+(" + _MONTH_ALT + r")\s+(\d{4})", re.IGNORECASE)
# Pojedynczy "listopad 2026" (caly miesiac)
R_MONTH_YEAR = re.compile(r"(?<![.\d])(" + _MONTH_ALT + r")\s+(\d{4})", re.IGNORECASE)
R_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
R_DMY = re.compile(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})")


@dataclass
class Window:
    nazwa: str
    od: date
    do: date


@dataclass
class GoldenMatch:
    nazwa: str
    okno: Window
    okres: tuple  # (date, date) - wykryty termin podrozy


def load_windows(profile: dict) -> list[Window]:
    out = []
    for w in (profile.get("zlote_terminy") or []):
        try:
            od = date.fromisoformat(str(w["od"]))
            do = date.fromisoformat(str(w["do"]))
        except (KeyError, ValueError, TypeError):
            logger.warning("Zlote terminy: pomijam nieprawidlowy wpis: %r", w)
            continue
        if do < od:
            od, do = do, od
        out.append(Window(nazwa=str(w.get("nazwa", "(bez nazwy)")), od=od, do=do))
    return out


def _mk(y: int, mo: int, d: int):
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def _order(a: date, b: date) -> tuple:
    return (a, b) if a <= b else (b, a)


def _month_interval(y: int, mo: int):
    try:
        start = date(y, mo, 1)
    except ValueError:
        return None, None
    end = date(y, 12, 31) if mo == 12 else date(y, mo + 1, 1) - timedelta(days=1)
    return start, end


def _infer_year(month: int, today: date) -> int:
    """Rok brakujacy w tekscie: ten sam rok, jesli miesiac jeszcze nie minal, inaczej nastepny."""
    _, end = _month_interval(today.year, month)
    return today.year if (end and end >= today) else today.year + 1


def _has_kw_near(low: str, pos: int, window: int = 70) -> bool:
    seg = low[max(0, pos - window):pos + window]
    return any(k in seg for k in TRAVEL_KW)


def _travel_periods(text: str, today: date) -> list[tuple]:
    """Zwraca liste okresow podrozy (date, date) wykrytych w tekscie."""
    low = text.lower()
    periods: list[tuple] = []
    consumed: list[tuple] = []

    def mark(m):
        consumed.append((m.start(), m.end()))

    def taken(m) -> bool:
        return any(not (m.end() <= s or m.start() >= e) for s, e in consumed)

    for m in R_ISO_RANGE.finditer(text):
        try:
            a, b = date.fromisoformat(m.group(1)), date.fromisoformat(m.group(2))
        except ValueError:
            continue
        periods.append(_order(a, b)); mark(m)

    for m in R_DMY_RANGE.finditer(text):
        a = _mk(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        b = _mk(int(m.group(6)), int(m.group(5)), int(m.group(4)))
        if a and b:
            periods.append(_order(a, b)); mark(m)

    for m in R_DM_RANGE.finditer(text):
        if taken(m):
            continue
        yr = int(m.group(5))
        a = _mk(yr, int(m.group(2)), int(m.group(1)))
        b = _mk(yr, int(m.group(4)), int(m.group(3)))
        if a and b:
            periods.append(_order(a, b)); mark(m)

    for m in R_DAYRANGE_MONTH.finditer(low):
        if taken(m):
            continue
        mon = MONTHS[m.group(3)]
        yr = int(m.group(4)) if m.group(4) else _infer_year(mon, today)
        a = _mk(yr, mon, int(m.group(1)))
        b = _mk(yr, mon, int(m.group(2)))
        if a and b:
            periods.append(_order(a, b)); mark(m)

    for m in R_MONTH_RANGE.finditer(low):
        if taken(m):
            continue
        m1, m2 = MONTHS[m.group(1)], MONTHS[m.group(3)]
        y2 = int(m.group(4)) if m.group(4) else (int(m.group(2)) if m.group(2) else _infer_year(m2, today))
        y1 = int(m.group(2)) if m.group(2) else y2
        s1, _ = _month_interval(y1, m1)
        _, e2 = _month_interval(y2, m2)
        if s1 and e2 and s1 <= e2:
            periods.append((s1, e2)); mark(m)

    for m in R_DAY_MONTH.finditer(low):
        if taken(m) or not _has_kw_near(low, m.start()):
            continue
        d = _mk(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
        if d:
            periods.append((d, d)); mark(m)

    for m in R_MONTH_YEAR.finditer(low):
        if taken(m) or not _has_kw_near(low, m.start()):
            continue
        s, e = _month_interval(int(m.group(2)), MONTHS[m.group(1)])
        if s and e:
            periods.append((s, e)); mark(m)

    for m in R_ISO.finditer(text):
        if taken(m) or not _has_kw_near(low, m.start()):
            continue
        d = _mk(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            periods.append((d, d)); mark(m)

    for m in R_DMY.finditer(text):
        if taken(m) or not _has_kw_near(low, m.start()):
            continue
        d = _mk(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        if d:
            periods.append((d, d)); mark(m)

    return periods


def match(text: str, windows: list[Window], today: date | None = None) -> GoldenMatch | None:
    """Zwraca pierwszy zloty termin (kolejnosc w config = priorytet), ktorego okno
    zachodzi na wykryty termin podrozy, albo None."""
    if not windows or not text:
        return None
    today = today or date.today()
    periods = _travel_periods(text, today)
    if not periods:
        return None
    for w in windows:
        for p in periods:
            if p[0] <= w.do and w.od <= p[1]:   # przeciecie przedzialow
                return GoldenMatch(nazwa=w.nazwa, okno=w, okres=p)
    return None


def tag(promo, gm: GoldenMatch) -> None:
    """Oznacza promocje jako trafienie w zloty termin (tag w regiony + notka w streszczeniu)."""
    if TAG not in promo.regiony:
        promo.regiony.append(TAG)
    okres = f"{gm.okres[0].isoformat()}...{gm.okres[1].isoformat()}"
    note = (f"Zloty termin '{gm.nazwa}': wykryty termin podrozy {okres} "
            f"wpada w Twoje okno urlopowe")
    base = (promo.streszczenie or "").rstrip(". ")
    promo.streszczenie = (base + ". " + note + ".") if base else (note + ".")
