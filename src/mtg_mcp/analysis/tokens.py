"""Token checklist for a deck."""

from __future__ import annotations

import re
from typing import Any

from ..decklist import ParsedDeck
from ..scryfall import oracle_text
from ._card_utils import _front_lower

_TOKEN_DOUBLERS = frozenset({
    "doubling season", "parallel lives", "anointed procession", "primal vigor",
    "mondrak, glory dominus", "adrix and nev, twincasters", "ojer taq, deepest foundation",
    "chatterfang, squirrel general",
})
_TOKEN_BATCH_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
_CREATE_TOKEN_RE = re.compile(
    r"creates?\s+(a|an|one|two|three|four|five|six|seven|eight|nine|ten|\d+|x)\s+([^.;\n]*?\btokens?)",
    re.IGNORECASE,
)


def collect_deck_tokens(deck: ParsedDeck, cards: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Identify every token and helper marker a deck creates and estimate how many copies to bring."""
    entries = [(e, cards.get(e.name.lower())) for e in deck.playing]
    resolved = [(e, c) for e, c in entries if c is not None]
    doublers = [c.get("name", e.name) for e, c in resolved if _front_lower(c.get("name", e.name)) in _TOKEN_DOUBLERS]

    by_token: dict[str, dict[str, Any]] = {}
    for e, c in resolved:
        card_name = c.get("name", e.name)
        text = oracle_text(c)
        text_low = text.lower()
        repeatable = bool(re.search(r"\bwhenever\b|\bat the beginning of\b|\beach (?:turn|combat|upkeep|end step)\b", text_low)) or ":" in text_low

        # 1. Scryfall all_parts token references if present; otherwise fallback to oracle regex
        parts = [p for p in (c.get("all_parts") or []) if p.get("component") == "token"]
        if parts:
            for part in parts:
                tname = part.get("name") or "Token"
                tkey = f"{tname}|{part.get('type_line', '')}".lower()
                scales = "for each" in text_low or "create x " in text_low
                item = by_token.setdefault(tkey, {
                    "name": tname,
                    "type_line": part.get("type_line", "Token"),
                    "scryfall_uri": part.get("uri"),
                    "sources": [],
                    "max_batch": 1,
                    "repeatable": False,
                    "scales": False,
                })
                if card_name not in item["sources"]:
                    item["sources"].append(card_name)
                item["repeatable"] = item["repeatable"] or repeatable
                item["scales"] = item["scales"] or scales
        else:
            for m in _CREATE_TOKEN_RE.finditer(text):
                cnt_raw, desc = m.group(1).lower(), m.group(2).strip()
                scales = cnt_raw == "x" or "for each" in text_low
                batch = 3 if scales else (_TOKEN_BATCH_WORDS.get(cnt_raw) or (int(cnt_raw) if cnt_raw.isdigit() else 1))
                tkey = re.sub(r"\btokens?\b", "token", desc.lower()).strip()
                item = by_token.setdefault(tkey, {
                    "name": desc,
                    "type_line": "Token",
                    "sources": [],
                    "max_batch": 1,
                    "repeatable": False,
                    "scales": False,
                })
                if card_name not in item["sources"]:
                    item["sources"].append(card_name)
                item["max_batch"] = max(item["max_batch"], batch)
                item["repeatable"] = item["repeatable"] or repeatable
                item["scales"] = item["scales"] or scales

    tokens_out = []
    for item in by_token.values():
        qty = max(len(item["sources"]), item["max_batch"])
        reasons: list[str] = []
        if len(item["sources"]) > 1:
            reasons.append(f"{len(item['sources'])} cards create it")
        elif item["max_batch"] > 1:
            reasons.append(f"creates {item['max_batch']} at once")
        if item["scales"]:
            qty = max(qty, 10)
            reasons.append("scales with board")
        elif item["repeatable"]:
            qty = max(qty, 6)
            reasons.append("repeatable trigger/ability")
        if doublers:
            qty *= 2
            reasons.append(f"doubled by {', '.join(doublers)}")
        qty = max(1, min(12, qty))
        tokens_out.append({
            "token": item["name"],
            "type_line": item["type_line"],
            "suggested_quantity": qty,
            "reason": ", ".join(reasons).capitalize() if reasons else "One-shot effect",
            "created_by": sorted(item["sources"]),
        })

    tokens_out.sort(key=lambda t: (-t["suggested_quantity"], t["token"]))
    return {
        "total_distinct_tokens": len(tokens_out),
        "total_suggested_cards": sum(t["suggested_quantity"] for t in tokens_out),
        "token_doublers_in_deck": doublers,
        "tokens": tokens_out,
    }
