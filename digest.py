from models import Promotion


def is_relevant(promo: Promotion, profile: dict) -> bool:
    typy = profile.get("typy_promocji") or []
    if typy and promo.typ not in typy:
        return False

    partnerzy = profile.get("partnerzy") or []
    if partnerzy and promo.partner:
        if promo.partner.lower() not in {p.lower() for p in partnerzy}:
            return False

    regiony = profile.get("regiony") or []
    if regiony and promo.regiony:
        if not set(r.lower() for r in promo.regiony) & {r.lower() for r in regiony}:
            return False

    min_bonus = profile.get("min_bonus_pct")
    if min_bonus is not None and promo.bonus_pct is not None and promo.bonus_pct < min_bonus:
        return False

    return True


def filter_for_profile(promotions: list[Promotion], profile: dict) -> list[Promotion]:
    return [p for p in promotions if is_relevant(p, profile)]


def format_digest(promotions: list[Promotion]) -> str:
    if not promotions:
        return "Brak nowych promocji dla Twojego profilu."

    lines = [f"Nowe promocje Miles & More ({len(promotions)}):", ""]
    for p in promotions:
        bonus = f" +{p.bonus_pct}%" if p.bonus_pct else ""
        partner = f" | partner: {p.partner}" if p.partner else ""
        wazne_do = f" | wazne do: {p.wazne_do}" if p.wazne_do else ""
        lines.append(f"* [{p.typ}]{bonus} {p.tytul}{partner}{wazne_do}")
        lines.append(f"  {p.streszczenie}")
        lines.append(f"  Zrodlo: {p.zrodlo_nazwa} - {p.zrodlo_url}")
        lines.append("")

    return "\n".join(lines)
