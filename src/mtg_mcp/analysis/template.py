"""Command Zone deckbuilding template targets and reports."""

from __future__ import annotations

from typing import Any

from ..library import ROLE_TO_ANALYSIS_ROLE, _TAG_TO_ROLE
from .roles import card_roles

# The Command Zone's Commander deckbuilding template (2025). Targets add up to
# 108 for 99 slots on purpose: ~9 cards should do double duty (e.g. a creature
# that ramps and draws). Players can override any number per call.
TEMPLATE_CATEGORIES: dict[str, dict[str, Any]] = {
    "lands": {
        "target": 38,
        "description": "Land cards.",
        "scryfall": "t:land",
    },
    "ramp": {
        "target": 10,
        "description": "Mana rocks, mana dorks, land-fetching spells, Treasure makers, extra land drops.",
        "scryfall": "otag:ramp",
    },
    "card_advantage": {
        "target": 12,
        "description": "Cards that draw or otherwise give you extra cards to play.",
        "scryfall": "otag:card-advantage",
    },
    "targeted_disruption": {
        "target": 12,
        "description": "One-for-one interaction: spot removal, counterspells, bounce, edicts.",
        "scryfall": "(otag:removal or otag:counterspell)",
    },
    "mass_disruption": {
        "target": 6,
        "description": "Board wipes and other effects that hit many things at once.",
        "scryfall": "otag:sweeper",
    },
    "plan": {
        "target": 30,
        "description": "Cards that advance the deck's own strategy: synergy pieces, payoffs, win conditions.",
        "scryfall": None,
    },
}

# Derive from library._TAG_TO_ROLE so decklist category tags and reference library tags never drift.
_ENTRY_CATEGORY_TO_ROLE = {
    tag: ROLE_TO_ANALYSIS_ROLE[role]
    for tag, role in _TAG_TO_ROLE.items()
    if role in ROLE_TO_ANALYSIS_ROLE
}
_CATEGORY_ROLES = {
    "ramp": {"ramp"},
    "card_advantage": {"card_draw"},
    "targeted_disruption": {"removal", "counterspell"},
    "mass_disruption": {"board_wipe"},
}


def resolve_template(overrides: dict[str, int] | None = None) -> dict[str, int]:
    """Default template targets with the player's overrides applied."""
    targets = {k: v["target"] for k, v in TEMPLATE_CATEGORIES.items()}
    for key, value in (overrides or {}).items():
        if key not in targets:
            raise ValueError(f"Unknown template category {key!r}; expected one of {', '.join(targets)}.")
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 99:
            raise ValueError(f"Template target for {key!r} must be a whole number from 0 to 99, got {value!r}.")
        targets[key] = value
    return targets


def template_overlap(targets: dict[str, int], slots: int = 99) -> dict[str, Any]:
    """How many cards must count in two categories for the targets to fit the deck."""
    total = sum(targets.values())
    return {
        "targets_total": total,
        "deck_slots": slots,
        "cards_doing_double_duty": max(total - slots, 0),
        "unassigned_slots": max(slots - total, 0),
    }


def _template_report(deck_cards: list[dict[str, Any]], lands: int, targets: dict[str, int], slots: int) -> dict[str, Any]:
    """Compare a deck against template targets. deck_cards are the resolved nonland cards."""
    members: dict[str, list[str]] = {k: [] for k in targets}
    for c in deck_cards:
        roles = set(card_roles(c))
        in_any = False
        for key, wanted in _CATEGORY_ROLES.items():
            if roles & wanted:
                members[key].append(c.get("name", "?"))
                in_any = True
        if not in_any:
            members["plan"].append(c.get("name", "?"))

    categories = {}
    gaps = []
    for key, target in targets.items():
        actual = lands if key == "lands" else len(members[key])
        diff = actual - target
        status = "on target" if diff == 0 else (f"{-diff} short" if diff < 0 else f"{diff} over")
        entry: dict[str, Any] = {"target": target, "actual": actual, "status": status}
        if key != "lands":
            entry["cards"] = sorted(members[key])
        categories[key] = entry
        # Over on lands is a real problem; over on a spell category usually just means overlap.
        if diff < 0 or (key == "lands" and diff > 0):
            gaps.append(f"{key}: {actual} (template target {target}, {status})")

    return {
        "categories": categories,
        "gaps": gaps,
        **template_overlap(targets, slots),
        "note": (
            "Spell categories are tagged heuristically from oracle text and a card can count in several; "
            "'plan' is every nonland card that fits none of the others. Verify borderline cards."
        ),
    }
