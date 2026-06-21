import logging
from typing import Literal

import anthropic
from pydantic import BaseModel

from models import Promotion

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5"

SYSTEM_PROMPT = """Jestes analitykiem programu Miles & More (Lufthansa). Otrzymujesz surowy tekst
z artykulu, wpisu RSS lub strony promocyjnej. Twoje zadanie: wykryc promocje Miles & More
(np. kup mile z bonusem, okazje mileowe, bonusy partnerskie, promocje kart) i opisac kazda
WLASNYMI SLOWAMI po polsku w 1-2 zwiezlych zdaniach (pole streszczenie). NIE kopiuj fragmentow
tekstu zrodlowego dluzszych niz kilka slow - to wymog prawny, nie sugestia.

Jesli tekst nie zawiera zadnej konkretnej promocji Miles & More, zwroc pusta liste w polu "promocje".
Jesli ktoregos pola nie da sie ustalic, ustaw je na null (lub pusta liste dla regiony/trasy)."""


class PromoItem(BaseModel):
    tytul: str
    typ: Literal["buy_miles", "mileage_bargain", "partner_bonus", "card", "other"]
    bonus_pct: int | None
    partner: str | None
    wazne_do: str | None
    regiony: list[str]
    trasy: list[str]
    streszczenie: str


class PromoExtraction(BaseModel):
    promocje: list[PromoItem]


def normalize_item(client: anthropic.Anthropic, raw_item: dict) -> list[Promotion]:
    """Wysyla surowy tekst do Claude i zwraca liste wykrytych promocji (bez hash_dedup/id)."""
    text = raw_item["tekst"][:8000]  # bezpieczny limit dla pojedynczego itemu

    try:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
            output_format=PromoExtraction,
        )
    except anthropic.BadRequestError as e:
        logger.warning("Normalize: zly request dla %s: %s", raw_item.get("zrodlo_url"), e)
        return []
    except anthropic.RateLimitError as e:
        logger.warning("Normalize: rate limit, pomijam item: %s", e)
        return []
    except anthropic.APIStatusError as e:
        logger.warning("Normalize: blad API (%s) dla %s", e.status_code, raw_item.get("zrodlo_url"))
        return []
    except anthropic.APIConnectionError as e:
        logger.warning("Normalize: blad polaczenia: %s", e)
        return []

    extraction = response.parsed_output
    promotions = []
    for item in extraction.promocje:
        promotions.append(
            Promotion(
                id="",
                tytul=item.tytul,
                typ=item.typ,
                bonus_pct=item.bonus_pct,
                partner=item.partner,
                wazne_do=item.wazne_do,
                regiony=item.regiony,
                trasy=item.trasy,
                zrodlo_url=raw_item["zrodlo_url"],
                zrodlo_nazwa=raw_item["zrodlo_nazwa"],
                streszczenie=item.streszczenie,
            )
        )
    return promotions
