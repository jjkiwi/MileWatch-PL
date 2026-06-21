from dataclasses import dataclass, field


@dataclass
class Promotion:
    id: str
    tytul: str
    typ: str  # buy_miles | mileage_bargain | partner_bonus | card | other
    bonus_pct: int | None
    partner: str | None
    wazne_do: str | None  # ISO date string, np. "2026-07-31", lub None
    regiony: list[str] = field(default_factory=list)
    trasy: list[str] = field(default_factory=list)
    zrodlo_url: str = ""
    zrodlo_nazwa: str = ""
    streszczenie: str = ""
    pierwszy_raz_widziane: str = ""  # ISO timestamp ustawiany przy zapisie
    hash_dedup: str = ""
