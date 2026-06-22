"""Uruchamia pipeline i generuje strone do GitHub Pages (docs/index.html).

Uzywane przez GitHub Actions (workflow .github/workflows/update.yml), zeby utrzymywac
darmowy, automatycznie aktualizowany WSPOLDZIELONY LINK z promocjami. Mozna tez
uruchomic recznie:  python publish.py
"""

import os

import export_html
import storage
from run import run_pipeline
from sources import load_profile

OUT_DIR = "docs"
OUT_FILE = os.path.join(OUT_DIR, "index.html")


def main() -> int:
    # 1) zbierz nowe promocje (scraping + ekstrakcja, w pelni darmowe)
    run_pipeline()

    # 2) wygeneruj strone ze WSZYSTKICH zapisanych promocji
    conn = storage.connect()
    promotions = storage.get_all_promotions(conn)
    conn.close()

    os.makedirs(OUT_DIR, exist_ok=True)
    export_html.write_export(promotions, load_profile(), OUT_FILE)
    print(f"Zapisano {len(promotions)} promocji do {OUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
