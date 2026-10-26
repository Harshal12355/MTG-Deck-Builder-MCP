"""Full deck analysis orchestrator."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from ..decklist import ParsedDeck
from ..scryfall import front_type_line, oracle_text, price_usd
from ._card_utils import COLORS, _pips
from .bracket import _is_game_changer, _score_and_bracket
from .legality import _copy_limit
from .roles import card_roles
from .template import _ENTRY_CATEGORY_TO_ROLE, _template_report, resolve_template

def analyze(
    deck: ParsedDeck,
    cards: dict[str, dict[str, Any]],
    *,
    fmt: str = "commander",
    budget_per_card: float | None = None,
    template: dict[str, int] | None = None,
    combos: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fmt = fmt.lower()
    targets = resolve_template(template)
    singleton = fmt in {"commander", "brawl", "standardbrawl", "oathbreaker", "duel", "paupercommander", "predh"}
    entries = [(e, cards.get(e.name.lower())) for e in deck.playing]
    resolved = [(e, c) for e, c in entries if c is not None]
    missing = [e.name for e, c in entries if c is None]

    total = sum(e.quantity for e, _ in entries)
    type_counts: Counter[str] = Counter()
    curve: Counter[str] = Counter()
    pips: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    roles: dict[str, list[str]] = defaultdict(list)
    nonland_cmc: list[float] = []
    lands = 0

    for e, c in resolved:
        tl = front_type_line(c)
        for t in ("Creature", "Instant", "Sorcery", "Artifact", "Enchantment", "Planeswalker", "Battle", "Land"):
            if t in tl:
                type_counts[t] += e.quantity
        is_land = "Land" in tl
        if is_land:
            lands += e.quantity
            produced = c.get("produced_mana") or []
            for color in COLORS:
                if color in produced:
                    sources[color] += e.quantity
        else:
            cmc = float(c.get("cmc") or 0)
            nonland_cmc.extend([cmc] * e.quantity)
            bucket = str(int(cmc)) if cmc < 7 else "7+"
            curve[bucket] += e.quantity
            cost = c.get("mana_cost") or ((c.get("card_faces") or [{}])[0].get("mana_cost", ""))
            p = _pips(cost)
            for k, v in p.items():
                pips[k] += v * e.quantity
        detected_roles = list(card_roles(c))
        if not is_land and not detected_roles and e.categories:
            for cat in e.categories:
                mapped = _ENTRY_CATEGORY_TO_ROLE.get(cat.strip().lower())
                if mapped and mapped not in detected_roles:
                    detected_roles.append(mapped)
        for r in detected_roles:
            roles[r].append(c.get("name", e.name))

    # ---- Commander colour identity ----
    commander_cards = [cards.get(e.name.lower()) for e in deck.commanders]
    identity: set[str] = set()
    for c in commander_cards:
        if c:
            identity |= set(c.get("color_identity") or [])

    # ---- Legality ----
    issues: list[str] = []
    if fmt == "commander":
        if total != 100:
            issues.append(f"Commander decks must be exactly 100 cards including the commander; this list has {total}.")
        if not deck.commanders:
            issues.append("No commander identified. Mark it with a 'Commander' section, *CMDR*, or pass it explicitly.")
    elif fmt in {"standard", "pioneer", "modern", "legacy", "vintage", "pauper", "historic", "timeless", "explorer", "alchemy"}:
        if total < 60:
            issues.append(f"{fmt.title()} decks need at least 60 main-deck cards; this list has {total}.")
        side = sum(e.quantity for e in deck.sideboard)
        if side > 15:
            issues.append(f"Sideboard has {side} cards; the maximum is 15.")

    not_legal: list[dict[str, str]] = []
    copies: Counter[str] = Counter()
    by_name: dict[str, dict[str, Any]] = {}
    for e, c in resolved:
        name = c.get("name", e.name)
        copies[name] += e.quantity
        by_name[name] = c
        status = (c.get("legalities") or {}).get(fmt)
        if status and status != "legal" and not (status == "restricted" and e.quantity == 1):
            not_legal.append({"card": name, "status": status})
        if identity and deck.commanders and fmt == "commander":
            outside = set(c.get("color_identity") or []) - identity
            if outside:
                issues.append(f"{name} is outside the commander's colour identity (has {''.join(sorted(outside))}).")
    for name, n in copies.items():
        limit = _copy_limit(by_name[name], singleton)
        if limit is not None and n > limit:
            issues.append(f"{n} copies of {name}; the limit is {limit}.")
    if not_legal:
        issues.append(f"{len(not_legal)} card(s) not legal in {fmt}: " + ", ".join(f"{x['card']} ({x['status']})" for x in not_legal))

    # ---- Price ----
    priced: list[tuple[str, float, int]] = []
    unpriced: list[str] = []
    for e, c in resolved:
        p = price_usd(c)
        if p is None:
            unpriced.append(c.get("name", e.name))
        else:
            priced.append((c.get("name", e.name), p, e.quantity))
    total_price = round(sum(p * q for _, p, q in priced), 2)
    priciest = sorted(priced, key=lambda x: -x[1])[:10]
    over_budget = [{"card": n, "usd": p} for n, p, _ in priced if budget_per_card is not None and p > budget_per_card]

    game_changers = sorted({c.get("name", e.name) for e, c in resolved if _is_game_changer(c, e.name)})

    # ---- Role comparison against rules of thumb ----
    role_counts = {r: len(v) for r, v in roles.items()}
    interaction = len(set(roles.get("removal", [])) | set(roles.get("counterspell", [])) | set(roles.get("board_wipe", [])))
    template_report = None
    nonland_all = [c for _, c in resolved if "Land" not in front_type_line(c)]
    if fmt == "commander":
        nonland = [c for e, c in resolved if "Land" not in front_type_line(c) and e not in deck.commanders]
        slots = 100 - max(len(deck.commanders), 1)
        template_report = _template_report(nonland, lands, targets, slots)

    avg_cmc = round(sum(nonland_cmc) / len(nonland_cmc), 2) if nonland_cmc else 0.0
    curve_order = ["0", "1", "2", "3", "4", "5", "6", "7+"]

    bracket_report, power_report, synergy_report, school_report = _score_and_bracket(
        resolved=resolved,
        nonland_cards=nonland_all,
        lands=lands,
        avg_cmc=avg_cmc,
        roles=roles,
        interaction_total=interaction,
        game_changers=game_changers,
        spellbook_combos=combos,
    )

    return {
        "format": fmt,
        "card_count": total,
        "commanders": [c.get("name") for c in commander_cards if c],
        "color_identity": "".join(c for c in COLORS if c in identity) or None,
        "legal": not issues,
        "legality_issues": issues,
        "bracket": bracket_report,
        "power_score": power_report,
        "school_score": school_report,
        "synergy": synergy_report,
        "types": dict(type_counts.most_common()),
        "mana_curve_nonland": {k: curve.get(k, 0) for k in curve_order},
        "average_cmc_nonland": avg_cmc,
        "lands": lands,
        "color_pips": {c: pips[c] for c in COLORS if pips[c]},
        "land_color_sources": {c: sources[c] for c in COLORS if sources[c]},
        "roles": {
            "counts": {**role_counts, "interaction_total": interaction},
            "cards": {r: sorted(v) for r, v in roles.items()},
            "note": (
                "Roles are tagged heuristically from oracle text; verify borderline cards. "
                "card_draw is every draw. draw_on_cast happens when the spell resolves, "
                "draw_on_hit waits for combat damage, draw_on_their_spell waits for an opponent to cast a spell. "
                "A draw with no gate still counts as card_draw."
            ),
        },
        "template": template_report,
        "game_changers": game_changers,
        "price": {
            "total_usd": total_price,
            "most_expensive": [{"card": n, "usd": p} for n, p, _ in priciest],
            "no_price_listed": unpriced,
            "over_budget": over_budget or None,
            "source": "Scryfall (TCGplayer market, cheapest listed finish of the printing Scryfall returned)",
        },
        "cards_not_found": missing,
        "sideboard_count": sum(e.quantity for e in deck.sideboard),
        "maybeboard_count": sum(e.quantity for e in deck.maybe),
    }
