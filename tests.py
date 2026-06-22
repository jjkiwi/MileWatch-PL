"""Testy regresyjne MileWatch PL - uruchom:  python tests.py

Sprawdzaja kluczowa logike: wykrywanie promocji Miles & More (PL/DE/EN), perelki
(bledy cenowe / tania biznes klasa), odsiewanie newsow, deduplikacje i filtr profilu.
Nie wymagaja sieci ani kluczy API.
"""

import sys

from extract import extract_from_item
from deals import detect_deal
from dedup import dedup_promotions, _same_structure
from digest import is_relevant
from models import Promotion

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
    print("\n[deals] perelki: bledy cenowe i tania biznes klasa")
    d = detect_deal(_item("Blad cenowy! Bangkok w ekonomii za 900 zl w obie strony"))
    check("blad cenowy -> error_fare", d and d.typ == "error_fare")

    d = detect_deal(_item("Tokio z Warszawy za 1399 PLN w obie strony - okazja"))
    check("mega-tani dalekodystansowy -> error_fare", d and d.typ == "error_fare")

    d = detect_deal(_item("Business class do Azji za 3200 zl, Qatar Airways"))
    check("tania biznes (3200 zl) -> business_class", d and d.typ == "business_class")
    check("biznes wykryl partnera Qatar", d and d.partner == "Qatar")

    d = detect_deal(_item("Business Class to New York for 750 EUR, Lufthansa"))
    check("tania biznes EUR -> business_class", d and d.typ == "business_class")

    check("zwykly europejski tani lot odrzucony",
          detect_deal(_item("Wakacyjne loty do Wloch od 145 PLN")) is None)
    check("droga biznes (9000 zl) odrzucona",
          detect_deal(_item("Business class do Tokio za 9000 zl - standard")) is None)
    check("drogi dalekodystansowy ekonom (3200 zl) odrzucony",
          detect_deal(_item("Loty do Tajlandii za 3200 zl w ekonomii")) is None)


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


def main():
    test_extract_miles()
    test_extract_rejects_news()
    test_deals()
    test_dedup()
    test_digest()
    print(f"\n=== WYNIK: {PASS} OK, {FAIL} FAIL ===")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
