"""Diagnostyka MileWatch PL - pokazuje, na ktorym etapie znikaja dane.

Uruchom:  python diag.py

Wypisuje dla kazdego zrodla: ile itemow pobrano, przyklady tytulow oraz ile
itemow przeszlo przez wykrywanie promocji (extract.py) i dlaczego.
"""

import logging

from extract import (MILES_SIGNALS, PROMO_SIGNALS, _contains_any,
                     extract_from_item)
from fetch_rss import fetch_rss_items
from fetch_scrape import fetch_scrape_items
from sources import load_sources

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    sources = load_sources()
    print(f"\nAktywne zrodla w config.yaml: {len(sources)}\n" + "=" * 60)

    total_items = 0
    total_promos = 0

    for s in sources:
        print(f"\nZRODLO: {s.name}  [{s.type}]\n  URL: {s.url}")
        try:
            if s.type == "rss":
                items = fetch_rss_items(s.name, s.url)
            else:
                items = fetch_scrape_items(s.name, s.url)
        except Exception as e:  # noqa: BLE001
            print(f"  !! BLAD POBIERANIA: {e}")
            continue

        total_items += len(items)
        print(f"  Pobrano itemow: {len(items)}")
        if not items:
            print("  -> 0 itemow. Zrodlo niedostepne, zmienilo adres, albo robots.txt blokuje.")
            continue

        # Przyklady tytulow (pierwsza linia tekstu)
        for it in items[:3]:
            first = (it["tekst"].strip().splitlines() or [""])[0][:80]
            print(f"     - {first}")

        # Ile przechodzi przez kazdy filtr
        miles_ok = sum(1 for it in items if _contains_any(it["tekst"].lower(), MILES_SIGNALS))
        promo_ok = sum(1 for it in items if _contains_any(it["tekst"].lower(), PROMO_SIGNALS))
        promos = [p for it in items for p in extract_from_item(it)]
        total_promos += len(promos)
        print(f"  Itemy z sygnalem Miles&More: {miles_ok}/{len(items)}")
        print(f"  Itemy z sygnalem promocji:   {promo_ok}/{len(items)}")
        print(f"  -> Wykryto promocji:         {len(promos)}")
        for p in promos[:3]:
            print(f"        [{p.typ}] +{p.bonus_pct}% {p.partner} do {p.wazne_do}")

    print("\n" + "=" * 60)
    print(f"RAZEM: pobrano {total_items} itemow, wykryto {total_promos} promocji.")
    if total_items == 0:
        print("Diagnoza: zadne zrodlo nie zwrocilo danych -> problem z siecia/adresami zrodel.")
    elif total_promos == 0:
        print("Diagnoza: dane sa, ale nic nie pasuje do filtra -> albo brak aktualnych")
        print("          promocji w feedach, albo filtr w extract.py jest za waski.")
    else:
        print("Diagnoza: pipeline dziala. Jesli GUI pokazuje 0, kliknij 'Odswiez promocje'.")


if __name__ == "__main__":
    main()
