import hashlib
import logging

from rapidfuzz import fuzz

from models import Promotion

logger = logging.getLogger(__name__)

FUZZY_THRESHOLD = 88


def compute_hash(promo: Promotion) -> str:
    key = f"{promo.typ}|{(promo.partner or '').lower().strip()}|{promo.tytul.lower().strip()}|{promo.wazne_do or ''}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _same_structure(a: Promotion, b: Promotion) -> bool:
    """Ta sama promocja zgloszona przez rozne serwisy ma czesto inny tytul,
    ale identyczne pola strukturalne (typ, partner, bonus, data waznosci).
    Przy ekstrakcji slow kluczowych to pewniejszy sygnal duplikatu niz sam tytul.
    """
    if a.typ != b.typ:
        return False
    if (a.partner or "").lower().strip() != (b.partner or "").lower().strip():
        return False
    if a.bonus_pct != b.bonus_pct:
        return False
    if (a.wazne_do or "") != (b.wazne_do or ""):
        return False
    # Sklejamy strukturalnie TYLKO gdy jest konkretny bonus % (mocny, odrozniajacy sygnal).
    # Inaczej rozne wpisy "[other] Lufthansa bez bonusu" bledne by sie zlewaly w jeden.
    return a.bonus_pct is not None


def _matches_any(promo: Promotion, others: list[Promotion]) -> bool:
    for other in others:
        if promo.typ != other.typ:
            continue
        if fuzz.token_sort_ratio(promo.tytul, other.tytul) >= FUZZY_THRESHOLD:
            return True
        if _same_structure(promo, other):
            return True
    return False


def dedup_promotions(promotions: list[Promotion], existing: list[Promotion]) -> list[Promotion]:
    """Usuwa duplikaty w obrebie biezacego batcha i wzgledem juz zapisanych promocji.

    Ustawia hash_dedup na kazdej promocji. Zwraca liste unikalnych promocji.
    """
    unique: list[Promotion] = []
    duplicate_count = 0

    for promo in promotions:
        promo.hash_dedup = compute_hash(promo)
        if _matches_any(promo, existing) or _matches_any(promo, unique):
            duplicate_count += 1
            continue
        unique.append(promo)

    logger.info(
        "Dedup: %d wejsciowych -> %d unikalnych, %d odrzuconych duplikatow",
        len(promotions),
        len(unique),
        duplicate_count,
    )
    return unique
