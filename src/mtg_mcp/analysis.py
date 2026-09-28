"""Deck analysis: curve, colors, card roles, legality and price.

Role tagging is a heuristic over oracle text. It is good enough to spot gaps
("you have 5 ramp pieces, most decks run ~10") but it is not a substitute for
reading the cards, so results say so.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

from .decklist import ParsedDeck
from .scryfall import front_type_line, oracle_text, price_usd

COLORS = "WUBRG"

# Rule-of-thumb targets for a 100-card Commander deck (the widely used
# "37 lands / 10 ramp / 10 draw / 10 interaction" template).
COMMANDER_TARGETS = {
    "lands": (35, 38),
    "ramp": (10, None),
    "card_draw": (10, None),
    "removal": (8, None),
    "board_wipe": (2, 4),
}

_ROLE_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "ramp": [
        re.compile(r"\badd (?:\{[wubrgcsx0-9/]+\}|one mana|two mana|three mana|x mana|an amount of|mana of any|that much)"),
        re.compile(r"search your library for (?:a|an|up to \w+|two) (?:basic )?(?:land|forest|plains|island|swamp|mountain)[^.]*onto the battlefield"),
        re.compile(r"put (?:a|an|up to \w+) (?:basic )?land cards? [^.]*onto the battlefield"),
        re.compile(r"you may play (?:an )?additional lands?"),
        re.compile(r"create (?:a|an|\w+) treasure token"),
    ],
    "card_draw": [
        re.compile(r"\bdraws? (?:a|an|one|two|three|four|five|x|that many|cards equal|\d+) (?:additional )?cards?"),
        re.compile(r"\bdraw cards equal"),
        re.compile(r"exile the top [^.]* cards? of your library[^.]*\. (?:until [^.]*, )?you may (?:play|cast)"),
    ],
    "removal": [
        re.compile(r"\b(?:destroy|exile) (?:target|up to (?:one|two|three|x) target|another target)"),
        re.compile(r"deals? (?:\d+|x|that much) damage to (?:any target|target (?:creature|planeswalker|attacking|blocking))"),
        re.compile(r"return (?:target|up to one target) (?:nonland permanent|creature|artifact|enchantment|permanent)[^.]* to its owner's hand"),
        re.compile(r"target (?:player|opponent) sacrifices"),
        re.compile(r"each opponent sacrifices"),
        re.compile(r"\bfights? (?:target|another target|up to one target)"),
        re.compile(r"target creature gets -\d+/-\d+|target creature gets -x/-x"),
    ],
    "counterspell": [re.compile(r"\bcounter (?:target|up to one target|that spell|it)\b")],
    "board_wipe": [
        re.compile(r"\b(?:destroy|exile) all (?:other )?(?:creatures|nonland permanents|permanents|artifacts|enchantments|nontoken)"),
        re.compile(r"\b(?:destroy|exile) each (?:other )?(?:creature|nonland permanent)"),
        re.compile(r"all (?:other )?creatures get -"),
        re.compile(r"deals? (?:\d+|x) damage to each (?:other )?creature"),
        re.compile(r"return all (?:other )?(?:creatures|nonland permanents|permanents)[^.]* to their owners' hands"),
        re.compile(r"each player sacrifices (?:all|each)"),
    ],
    "tutor": [re.compile(r"search your library for (?:a|an|up to \w+) (?!basic )(?![^.]*\bland\b)[^.]*card")],
    "protection": [
        re.compile(r"(?:gains?|have|has) (?:[a-z ,]*)?(?:hexproof|indestructible|shroud|protection from)"),
        re.compile(r"phase out"),
    ],
    "recursion": [
        re.compile(r"return [^.]*from your graveyard to (?:your hand|the battlefield)"),
        re.compile(r"(?:cast|play) [^.]* from your graveyard"),
    ],
}

_ANY_NUMBER = re.compile(r"a deck can have any number of cards named")
_UP_TO_N = re.compile(r"a deck can have up to (\w+) cards named")
_PIP = re.compile(r"\{([^}]+)\}")


def card_roles(card: dict[str, Any]) -> list[str]:
    if "Land" in front_type_line(card):
        return []
    text = oracle_text(card).lower()
    # Ignore reminder text in parentheses.
    text = re.sub(r"\([^)]*\)", "", text)
    roles = [role for role, pats in _ROLE_PATTERNS.items() if any(p.search(text) for p in pats)]
    # Mana rocks/dorks: "{T}: Add" on a nonland permanent.
    if "ramp" not in roles and re.search(r"\{t\}[^:]*: add\b", text):
        roles.insert(0, "ramp")
    return roles


def _pips(cost: str) -> Counter[str]:
    pips: Counter[str] = Counter()
    for sym in _PIP.findall(cost or ""):
        for c in COLORS:
            if c in sym.upper():
                pips[c] += 1
    return pips


def _is_basic(card: dict[str, Any]) -> bool:
    return "Basic" in (card.get("type_line") or "") and "Land" in (card.get("type_line") or "")


def _copy_limit(card: dict[str, Any], singleton: bool) -> int | None:
    """Max copies allowed; None means unlimited."""
    text = oracle_text(card).lower()
    if _is_basic(card) or _ANY_NUMBER.search(text):
        return None
    m = _UP_TO_N.search(text)
    if m:
        words = {"seven": 7, "nine": 9}
        return words.get(m.group(1), int(m.group(1)) if m.group(1).isdigit() else None)
    return 1 if singleton else 4


def analyze(
    deck: ParsedDeck,
    cards: dict[str, dict[str, Any]],
    *,
    fmt: str = "commander",
    budget_per_card: float | None = None,
) -> dict[str, Any]:
    fmt = fmt.lower()
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
        for r in card_roles(c):
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

    game_changers = sorted({c.get("name", e.name) for e, c in resolved if c.get("game_changer")})

    # ---- Role comparison against rules of thumb ----
    role_counts = {r: len(v) for r, v in roles.items()}
    interaction = len(set(roles.get("removal", [])) | set(roles.get("counterspell", [])) | set(roles.get("board_wipe", [])))
    gaps: list[str] = []
    if fmt == "commander":
        counts = {"lands": lands, **role_counts}
        for key, (lo, hi) in COMMANDER_TARGETS.items():
            n = counts.get(key, 0)
            if lo is not None and n < lo:
                gaps.append(f"{key}: {n} (typical is {lo}{'-' + str(hi) if hi else '+'})")
            elif hi is not None and n > hi:
                gaps.append(f"{key}: {n} (typical is {lo}-{hi})")

    avg_cmc = round(sum(nonland_cmc) / len(nonland_cmc), 2) if nonland_cmc else 0.0
    curve_order = ["0", "1", "2", "3", "4", "5", "6", "7+"]

    return {
        "format": fmt,
        "card_count": total,
        "commanders": [c.get("name") for c in commander_cards if c],
        "color_identity": "".join(c for c in COLORS if c in identity) or None,
        "legal": not issues,
        "legality_issues": issues,
        "types": dict(type_counts.most_common()),
        "mana_curve_nonland": {k: curve.get(k, 0) for k in curve_order},
        "average_cmc_nonland": avg_cmc,
        "lands": lands,
        "color_pips": {c: pips[c] for c in COLORS if pips[c]},
        "land_color_sources": {c: sources[c] for c in COLORS if sources[c]},
        "roles": {
            "counts": {**role_counts, "interaction_total": interaction},
            "cards": {r: sorted(v) for r, v in roles.items()},
            "note": "Roles are tagged heuristically from oracle text; verify borderline cards.",
        },
        "gaps_vs_typical_commander_deck": gaps if fmt == "commander" else None,
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
