import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from models import Promotion

SCHEMA = """
CREATE TABLE IF NOT EXISTS promotions (
    id TEXT PRIMARY KEY,
    tytul TEXT NOT NULL,
    typ TEXT NOT NULL,
    bonus_pct INTEGER,
    partner TEXT,
    wazne_do TEXT,
    regiony TEXT,
    trasy TEXT,
    zrodlo_url TEXT,
    zrodlo_nazwa TEXT,
    streszczenie TEXT,
    pierwszy_raz_widziane TEXT NOT NULL,
    hash_dedup TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS notified (
    promo_id TEXT PRIMARY KEY,
    notified_at TEXT NOT NULL
);
"""


def connect(db_path: str = "data/milewatch.db") -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


SELECT_COLUMNS = (
    "id, tytul, typ, bonus_pct, partner, wazne_do, regiony, trasy, "
    "zrodlo_url, zrodlo_nazwa, streszczenie, pierwszy_raz_widziane, hash_dedup"
)


def _row_to_promotion(row: tuple) -> Promotion:
    return Promotion(
        id=row[0],
        tytul=row[1],
        typ=row[2],
        bonus_pct=row[3],
        partner=row[4],
        wazne_do=row[5],
        regiony=row[6].split(",") if row[6] else [],
        trasy=row[7].split(",") if row[7] else [],
        zrodlo_url=row[8],
        zrodlo_nazwa=row[9],
        streszczenie=row[10],
        pierwszy_raz_widziane=row[11],
        hash_dedup=row[12],
    )


def get_known_hashes(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT hash_dedup FROM promotions").fetchall()
    return {row[0] for row in rows}


def get_recent_promotions(conn: sqlite3.Connection) -> list[Promotion]:
    """Zwraca promocje, ktore jeszcze nie wygasly (lub bez daty wygasniecia), do porownania fuzzy."""
    today = datetime.now(timezone.utc).date().isoformat()
    rows = conn.execute(
        f"SELECT {SELECT_COLUMNS} FROM promotions WHERE wazne_do IS NULL OR wazne_do >= ?",
        (today,),
    ).fetchall()
    return [_row_to_promotion(row) for row in rows]


def get_all_promotions(conn: sqlite3.Connection) -> list[Promotion]:
    """Zwraca wszystkie zapisane promocje (cala historia), najnowsze pierwsze."""
    rows = conn.execute(
        f"SELECT {SELECT_COLUMNS} FROM promotions ORDER BY pierwszy_raz_widziane DESC"
    ).fetchall()
    return [_row_to_promotion(row) for row in rows]


def get_unnotified_promotions(conn: sqlite3.Connection) -> list[Promotion]:
    """Zwraca nieprzedawnione promocje, dla ktorych nie wyslano jeszcze alertu Telegram.

    Niezalezne od "nowosci" w danym uruchomieniu run.py - jesli wyslanie alertu wczesniej
    sie nie udalo (np. blad sieci), promocja zostanie ponownie zakwalifikowana tutaj.
    """
    today = datetime.now(timezone.utc).date().isoformat()
    rows = conn.execute(
        f"SELECT {SELECT_COLUMNS} FROM promotions "
        "WHERE (wazne_do IS NULL OR wazne_do >= ?) "
        "AND id NOT IN (SELECT promo_id FROM notified)",
        (today,),
    ).fetchall()
    return [_row_to_promotion(row) for row in rows]


def mark_notified(conn: sqlite3.Connection, promo_id: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO notified (promo_id, notified_at) VALUES (?, ?)",
        (promo_id, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def save_promotion(conn: sqlite3.Connection, promo: Promotion) -> bool:
    """Zapisuje promocje jesli hash_dedup jest nowy. Zwraca True jesli zapisano (nowa)."""
    promo.pierwszy_raz_widziane = datetime.now(timezone.utc).isoformat()
    try:
        conn.execute(
            """
            INSERT INTO promotions
                (id, tytul, typ, bonus_pct, partner, wazne_do, regiony, trasy,
                 zrodlo_url, zrodlo_nazwa, streszczenie, pierwszy_raz_widziane, hash_dedup)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                promo.id,
                promo.tytul,
                promo.typ,
                promo.bonus_pct,
                promo.partner,
                promo.wazne_do,
                ",".join(promo.regiony),
                ",".join(promo.trasy),
                promo.zrodlo_url,
                promo.zrodlo_nazwa,
                promo.streszczenie,
                promo.pierwszy_raz_widziane,
                promo.hash_dedup,
            ),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
