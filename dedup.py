import hashlib
import logging

from rapidfuzz import fuzz

from models import Promotion

logger = logging.getLogger(__name__)

FUZZY_THRESHOLD = 88


def compute_hash(promo: Promotion) -> str:
    key = f"{promo.typ}|{(promo.partner or '').lower().strip()}|{promo.tytul.lower().strip()}|{promo.wazne_do or ''}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _matches_any(promo: Promotion, others: list[Promotion]) -> bool:
    for other in others:
        if promo.typ != other.typ:
            continue
        if fuzz.token_sort_ratio(promo.tytul, other.tytul) >= FUZZY_THRESHOLD:
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
