"""Commander Spellbook combo lookup (https://commanderspellbook.com).

Uses the public ``find-my-combos`` endpoint of the open-source backend
(github.com/SpaceCowMedia/commander-spellbook-backend).
"""

from __future__ import annotations

from typing import Any

from .decklist import ParsedDeck
from .http import HttpClient

BASE = "https://backend.commanderspellbook.com"
TTL = 6 * 3600

# Response keys (camelCase) -> friendlier names, in the order we report them.
BUCKETS = {
    "included": "in_deck",
    "almostIncluded": "one_card_away",
    "includedByChangingCommanders": "in_deck_with_different_commander",
    "almostIncludedByAddingColors": "one_card_away_needs_other_colors",
}


def _summarize_variant(v: dict[str, Any], deck_names: set[str]) -> dict[str, Any]:
    cards = [u.get("card", {}).get("name") for u in v.get("uses", [])]
    templates = [r.get("template", {}).get("name") for r in v.get("requires", [])]
    missing = [c for c in cards if c and c.lower() not in deck_names]
    out = {
        "id": v.get("id"),
        "cards": cards,
        "missing": missing or None,
        "also_requires": [t for t in templates if t] or None,
        "produces": [p.get("feature", {}).get("name") for p in v.get("produces", [])],
        "color_identity": v.get("identity"),
        "mana_needed": v.get("manaNeeded") or None,
        "prerequisites": " ".join(x for x in (v.get("easyPrerequisites"), v.get("notablePrerequisites")) if x) or None,
        "steps": v.get("description"),
        "bracket_tag": (v.get("bracketTag") or {}).get("name") if isinstance(v.get("bracketTag"), dict) else v.get("bracketTag"),
        "popularity": v.get("popularity"),
        "url": f"https://commanderspellbook.com/combo/{v.get('id')}/" if v.get("id") else None,
    }
    return {k: val for k, val in out.items() if val not in (None, [], "")}


class Spellbook:
    def __init__(self, http: HttpClient):
        self.http = http

    async def find_my_combos(self, deck: ParsedDeck, *, limit_per_bucket: int = 15, include_steps: bool = True) -> dict[str, Any]:
        body = {
            "commanders": [{"card": e.name, "quantity": e.quantity} for e in deck.commanders],
            "main": [{"card": e.name, "quantity": e.quantity} for e in deck.main],
        }
        data = await self.http.post(f"{BASE}/find-my-combos", body, ttl=TTL)
        results = data.get("results", data)
        deck_names = {e.name.lower() for e in deck.playing}
        out: dict[str, Any] = {"color_identity": results.get("identity")}
        for key, label in BUCKETS.items():
            variants = results.get(key) or []
            # Most popular first so the model sees the combos people actually play.
            variants = sorted(variants, key=lambda v: -(v.get("popularity") or 0))
            summarized = [_summarize_variant(v, deck_names) for v in variants[:limit_per_bucket]]
            if not include_steps:
                for s in summarized:
                    s.pop("steps", None)
                    s.pop("prerequisites", None)
            out[label] = {"total": len(variants), "combos": summarized}
        out["source"] = "Commander Spellbook"
        return out

    async def search(self, query: str, limit: int = 10) -> dict[str, Any]:
        """Search combos with Spellbook's query syntax, e.g. ``card:"Thassa's Oracle"``."""
        data = await self.http.get(f"{BASE}/variants/", params={"q": query, "limit": limit, "ordering": "-popularity"}, ttl=TTL)
        variants = data.get("results", [])
        return {
            "total": data.get("count", len(variants)),
            "combos": [_summarize_variant(v, set()) for v in variants[:limit]],
            "source": "Commander Spellbook",
        }
