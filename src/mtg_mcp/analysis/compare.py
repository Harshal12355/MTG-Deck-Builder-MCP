"""Side-by-side deck comparison."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ..decklist import ParsedDeck

def compare_decks_analysis(
    deck_a: ParsedDeck,
    deck_b: ParsedDeck,
    cards: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Compare two decklists side by side (EDHcheck Deck Compare)."""
    counts_a: Counter[str] = Counter()
    counts_b: Counter[str] = Counter()
    display: dict[str, str] = {}
    for e in deck_a.playing:
        c = cards.get(e.name.lower())
        name = c.get("name", e.name) if c else e.name
        key = name.lower()
        display[key] = name
        counts_a[key] += e.quantity
    for e in deck_b.playing:
        c = cards.get(e.name.lower())
        name = c.get("name", e.name) if c else e.name
        key = name.lower()
        display[key] = name
        counts_b[key] += e.quantity

    all_keys = sorted(set(counts_a) | set(counts_b))
    added = [{"card": display[k], "qty": counts_b[k] - counts_a[k]} for k in all_keys if counts_b[k] > counts_a[k]]
    removed = [{"card": display[k], "qty": counts_a[k] - counts_b[k]} for k in all_keys if counts_a[k] > counts_b[k]]
    shared = sum(min(counts_a[k], counts_b[k]) for k in all_keys)
    union = max(1, sum(max(counts_a[k], counts_b[k]) for k in all_keys))
    similarity_pct = round(shared / union * 100, 1)

    from .analyze import analyze

    rep_a = analyze(deck_a, cards)
    rep_b = analyze(deck_b, cards)

    def delta(val_a: float, val_b: float, ndigits: int = 2) -> dict[str, Any]:
        diff = round(val_b - val_a, ndigits)
        return {"before": val_a, "after": val_b, "delta": diff}

    return {
        "commanders_before": rep_a["commanders"],
        "commanders_after": rep_b["commanders"],
        "similarity_pct": similarity_pct,
        "cards_added": added,
        "cards_removed": removed,
        "deltas": {
            "bracket": delta(rep_a["bracket"]["bracket"], rep_b["bracket"]["bracket"], 0),
            "power_score": delta(rep_a["power_score"]["total"], rep_b["power_score"]["total"], 1),
            "speed": delta(rep_a["power_score"]["speed"], rep_b["power_score"]["speed"], 1),
            "consistency": delta(rep_a["power_score"]["consistency"], rep_b["power_score"]["consistency"], 1),
            "school_score": delta(rep_a["school_score"]["total"], rep_b["school_score"]["total"], 1),
            "average_cmc_nonland": delta(rep_a["average_cmc_nonland"], rep_b["average_cmc_nonland"], 2),
            "lands": delta(rep_a["lands"], rep_b["lands"], 0),
            "ramp": delta(rep_a["roles"]["counts"].get("ramp", 0), rep_b["roles"]["counts"].get("ramp", 0), 0),
            "card_draw": delta(rep_a["roles"]["counts"].get("card_draw", 0), rep_b["roles"]["counts"].get("card_draw", 0), 0),
            "interaction_total": delta(rep_a["roles"]["counts"].get("interaction_total", 0), rep_b["roles"]["counts"].get("interaction_total", 0), 0),
            "tutors": delta(rep_a["roles"]["counts"].get("tutor", 0), rep_b["roles"]["counts"].get("tutor", 0), 0),
            "game_changers": delta(len(rep_a["game_changers"]), len(rep_b["game_changers"]), 0),
            "price_usd": delta(rep_a["price"]["total_usd"], rep_b["price"]["total_usd"], 2),
        },
        "game_changers_added": sorted(set(rep_b["game_changers"]) - set(rep_a["game_changers"])),
        "game_changers_removed": sorted(set(rep_a["game_changers"]) - set(rep_b["game_changers"])),
    }
