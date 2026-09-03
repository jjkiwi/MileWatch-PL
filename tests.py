"""Testy regresyjne MileWatch PL - uruchom:  python tests.py

Sprawdzaja kluczowa logike: wykrywanie promocji Miles & More (PL/DE/EN), perelki
(bledy cenowe / tania biznes klasa), odsiewanie newsow, deduplikacje i filtr profilu.
Nie wymagaja sieci ani kluczy API.
"""

import sys

from datetime import date

import golden
from extract import extract_from_item
from deals import detect_deal
from dedup import dedup_promotions, _same_structure
from digest import is_relevant
from models import Promotion
from scoring import score_promo

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  OK   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}")


def _item(text):
    return {"tekst": text, "zrodlo_url": "http://x", "zrodlo_nazwa": "Test"}


def test_extract_miles():
    print("\n[extract] promocje Miles & More")
    r = extract_from_item(_item("Kup mile Miles & More z bonusem do 100%! Wazne do 31.07.2026 Lufthansa."))
    check("PL kup mile -> buy_miles", r and r[0].typ == "buy_miles")
    check("PL bonus 100%", r and r[0].bonus_pct == 100)
    check("PL data 2026-07-31", r and r[0].wazne_do == "2026-07-31")
    check("PL partner Lufthansa", r and r[0].partner == "Lufthansa")

    r = extract_from_item(_item("Miles & More Aktion: Meilen kaufen mit bis zu 75% Bonus, Lufthansa"))
    check("DE meilen kaufen -> buy_miles", r and r[0].typ == "buy_miles")
    check("DE bonus 75%", r and r[0].bonus_pct == 75)

    r = extract_from_item(_item("Miles & More offer: earn double miles with Marriott, up to 50% bonus"))
    check("EN partner -> partner_bonus", r and r[0].typ == "partner_bonus")
    check("EN partner Marriott", r and r[0].partner == "Marriott")


def test_extract_rejects_news():
    print("\n[extract] odsiewanie newsow i niezwiazanych")
    check("news '90 Prozent udzialow' odsiany",
          extract_from_item(_item("Lufthansa erhoeht Anteil an ITA Airways auf 90 Prozent - news")) == [])
    check("brak sygnalu M&M -> pusto",
          extract_from_item(_item("Air France serwuje nowe koktajle na pokladzie")) == [])
    check("tytul strony 'Miles & More Archive' (other, bez bonusu/daty) odsiany",
          extract_from_item(_item("Miles & More Archive - InsideFlyer DE bonus")) == [])


def test_deals():
    print("\n[deals] perelki: blad cenowy / tani lot / biznes + filtr wylotu")
    # Faza 0: blad cenowy TYLKO przy jawnym sygnale
    d = detect_deal(_item("Blad cenowy! Bangkok z Warszawy za 900 zl w obie strony"))
    check("jawny blad cenowy -> error_fare", d and d.typ == "error_fare")

    # Faza 0: zwykla promka z hype to TANI LOT, nie blad cenowy (zgloszony bug)
    d = detect_deal(_item("Rekordowo tanio! Loty do Szwecji z Warszawy za 150 zl"))
    check("hype + tani lot -> great_deal (nie error_fare)", d and d.typ == "great_deal")

    d = detect_deal(_item("Tokio z Warszawy za 1399 PLN w obie strony - okazja"))
    check("mega-tani dalekodystansowy -> great_deal", d and d.typ == "great_deal")

    d = detect_deal(_item("Business class do Azji z Warszawy za 3200 zl, Qatar Airways"))
    check("tania biznes (3200 zl) -> business_class", d and d.typ == "business_class")
    check("biznes wykryl partnera Qatar", d and d.partner == "Qatar")

    check("zwykly europejski bez hype odrzucony",
          detect_deal(_item("Wakacyjne loty do Wloch od 145 PLN")) is None)
    check("droga biznes (9000 zl) odrzucona",
          detect_deal(_item("Business class do Tokio za 9000 zl - standard")) is None)

    # Faza 1: priorytet lotnisk wylotu (zagraniczne perelki zostaja, ale bez alertu).
    # Uwaga: wpis musi byc realna okazja (cena ponizej progu), inaczej w ogole nie jest perelka.
    d_us = detect_deal(_item("Mega okazja: Los Angeles - Tokio za 1200 zl roundtrip"))
    check("zagraniczna perelka zostaje, oznaczona 'Wylot zagraniczny'",
          d_us is not None and "Wylot zagraniczny" in d_us.regiony)
    check("zagraniczna perelka NIE jest alarmowana",
          d_us is not None and not is_relevant(d_us, {}))
    d_pl = detect_deal(_item("Mega okazja: Warszawa - Bangkok za 1400 zl"))
    check("wylot z PL zostaje i jest alarmowany",
          d_pl is not None and "Wylot zagraniczny" not in d_pl.regiony
          and is_relevant(d_pl, {}))


def test_dedup():
    print("\n[dedup] deduplikacja")
    a = Promotion(id="", tytul="Kup mile +100% Lufthansa", typ="buy_miles", bonus_pct=100,
                  partner="Lufthansa", wazne_do="2026-07-31")
    b = Promotion(id="", tytul="Inny tytul tej samej promocji", typ="buy_miles", bonus_pct=100,
                  partner="Lufthansa", wazne_do="2026-07-31")
    check("strukturalny dedup laczy te sama promocje z bonusem", _same_structure(a, b))

    n1 = Promotion(id="", tytul="Newsy A", typ="other", bonus_pct=None, partner="Lufthansa", wazne_do=None)
    n2 = Promotion(id="", tytul="Newsy B", typ="other", bonus_pct=None, partner="Lufthansa", wazne_do=None)
    check("rozne newsy bez bonusu NIE sa sklejane", not _same_structure(n1, n2))

    uniq = dedup_promotions([a, b], [])
    check("dwie wersje -> jedna unikalna", len(uniq) == 1)


def test_digest():
    print("\n[digest] filtr profilu i perelki")
    prof = {"typy_promocji": ["buy_miles"], "partnerzy": ["Lufthansa"],
            "regiony": ["Europa", "Polska"], "min_bonus_pct": 20}
    ef = Promotion(id="", tytul="x", typ="error_fare", bonus_pct=None, partner=None,
                   wazne_do=None, regiony=["Dalekie loty"])
    check("error_fare zawsze relevant (mimo profilu)", is_relevant(ef, prof))
    bc = Promotion(id="", tytul="x", typ="business_class", bonus_pct=None, partner=None,
                   wazne_do=None, regiony=["Dalekie loty"])
    check("business_class zawsze relevant", is_relevant(bc, prof))
    weak = Promotion(id="", tytul="x", typ="buy_miles", bonus_pct=10, partner="Lufthansa",
                     wazne_do=None, regiony=["Europa"])
    check("buy_miles bonus 10% < min 20 -> nierelevant", not is_relevant(weak, prof))


def test_scoring():
    print("\n[scoring] ocena 0-100")
    ef = Promotion(id="", tytul="x", typ="error_fare", bonus_pct=None, partner=None,
                   wazne_do=None, regiony=["Dalekie loty"])
    gd_pl = Promotion(id="", tytul="x", typ="great_deal", bonus_pct=None, partner=None,
                      wazne_do=None, regiony=["Dalekie loty"])
    gd_zagr = Promotion(id="", tytul="x", typ="great_deal", bonus_pct=None, partner=None,
                        wazne_do=None, regiony=["Dalekie loty", "Wylot zagraniczny"])
    other = Promotion(id="", tytul="x", typ="other", bonus_pct=None, partner=None,
                      wazne_do=None, regiony=[])
    check("blad cenowy ma wysoki score (>=80)", score_promo(ef) >= 80)
    check("zagraniczny tani lot < krajowy tani lot",
          score_promo(gd_zagr) < score_promo(gd_pl))
    check("zwykly 'other' ma niski score (<30)", score_promo(other) < 30)
    check("score zawsze 0-100", 0 <= score_promo(gd_zagr) <= 100)


def test_baseline():
    print("\n[baseline] historia cen i wykrywanie rekordu")
    import sqlite3
    import baseline

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE price_history (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                 "route TEXT, currency TEXT, amount INTEGER, ts TEXT)")

    def mk(t):
        return Promotion(id="", tytul=t, typ="great_deal", bonus_pct=None, partner=None,
                         wazne_do=None, regiony=["Dalekie loty"], streszczenie="")

    for t in ["Szwecja za 150 zl", "Szwecja za 160 zl", "Szwecja za 140 zl", "Szwecja za 155 zl"]:
        baseline.record(conn, baseline.assess(conn, mk(t)))

    p_norm = mk("Szwecja za 150 zl")
    baseline.assess(conn, p_norm)
    check("typowa cena (150) NIE jest rekordem", "Rekord cenowy" not in p_norm.regiony)

    p_rec = mk("Szwecja za 90 zl")
    baseline.assess(conn, p_rec)
    check("rekordowo niska cena (90) = Rekord cenowy", "Rekord cenowy" in p_rec.regiony)
    check("rekord podbija scoring", score_promo(p_rec) > score_promo(p_norm))


def test_golden():
    print("\n[golden] zlote terminy: okna urlopowe -> alert o lotach w tym okresie")
    TODAY = date(2026, 8, 26)
    windows = golden.load_windows({"zlote_terminy": [
        {"nazwa": "Lato", "od": "2026-07-15", "do": "2026-09-10"},
        {"nazwa": "Swieta", "od": "2026-12-20", "do": "2027-01-03"},
    ]})
    check("wczytano 2 okna", len(windows) == 2)

    # Dopasowanie terminu podrozy do okna (zakres miesiecy, DE, zakres dni, miejscownik PL)
    m = golden.match("Tanie loty, terminy podrozy: sierpien-wrzesien 2026", windows, TODAY)
    check("zakres miesiecy trafia w okno Lato", m is not None and m.nazwa == "Lato")
    m = golden.match("Reisezeitraum: 01.09.2026 - 20.09.2026", windows, TODAY)
    check("DE Reisezeitraum (zakres dat) trafia", m is not None)
    m = golden.match("Lec w sierpniu 2026 na urlop", windows, TODAY)
    check("miejscownik 'w sierpniu' trafia w Lato", m is not None and m.nazwa == "Lato")

    # Zbyt dlugi okres (szeroka waznosc taryfy, nie termin urlopu) -> pomijany
    check("10-miesieczna waznosc taryfy NIE jest zlotym terminem",
          golden.match("Reisezeitraum September 2026 bis Juni 2027", windows, TODAY) is None)
    check("celowany miesiac (wrzesien) nadal trafia",
          golden.match("loty tylko we wrzesniu 2026", windows, TODAY) is not None)

    # Brak trafienia: poza oknami / brak terminu / data waznosci (nie termin lotu)
    check("listopad poza oknami -> brak",
          golden.match("wyloty listopad 2026", windows, TODAY) is None)
    check("data waznosci promocji != termin lotu -> brak",
          golden.match("Promocja wazna do 31.12.2026", windows, TODAY) is None)
    check("brak jakiejkolwiek daty -> brak",
          golden.match("Super promocja Miles & More", windows, TODAY) is None)

    # Tagowanie promocji
    p = Promotion(id="", tytul="Tokio", typ="great_deal", bonus_pct=None, partner=None,
                  wazne_do=None, regiony=["Dalekie loty"], streszczenie="Tani lot.")
    gm = golden.match("Tokio, podroz we wrzesniu 2026", windows, TODAY)
    golden.tag(p, gm)
    check("tag() dodaje 'Zloty termin' do regiony", "Zloty termin" in p.regiony)
    check("tag() dopisuje notke do streszczenia", "Zloty termin" in p.streszczenie)

    # Scoring: zloty termin mocno podbija ocene
    base = Promotion(id="", tytul="x", typ="great_deal", bonus_pct=None, partner=None,
                     wazne_do=None, regiony=["Dalekie loty"])
    gold = Promotion(id="", tytul="x", typ="great_deal", bonus_pct=None, partner=None,
                     wazne_do=None, regiony=["Dalekie loty", "Zloty termin"])
    check("zloty termin podbija scoring", score_promo(gold) > score_promo(base))

    # is_relevant: zloty termin zawsze alertowany (nawet wbrew profilowi), wyjatek: wylot zagr.
    restrykcyjny = {"typy_promocji": ["buy_miles"], "partnerzy": ["LOT"],
                    "regiony": ["Polska"], "min_bonus_pct": 90}
    zloty_pl = Promotion(id="", tytul="x", typ="great_deal", bonus_pct=None, partner=None,
                         wazne_do=None, regiony=["Zloty termin"])
    check("zloty termin alertowany mimo restrykcyjnego profilu", is_relevant(zloty_pl, restrykcyjny))
    zloty_zagr = Promotion(id="", tytul="x", typ="great_deal", bonus_pct=None, partner=None,
                           wazne_do=None, regiony=["Zloty termin", "Wylot zagraniczny"])
    check("zloty termin z wylotem zagranicznym NIE jest alertowany", not is_relevant(zloty_zagr, {}))


def main():
    test_extract_miles()
    test_extract_rejects_news()
    test_deals()
    test_dedup()
    test_digest()
    test_scoring()
    test_baseline()
    test_golden()
    print(f"\n=== WYNIK: {PASS} OK, {FAIL} FAIL ===")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
