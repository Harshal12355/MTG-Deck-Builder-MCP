"""Archidekt deck search and deck lookup (https://archidekt.com).

Archidekt has no official public API documentation; its website reads JSON from
``archidekt.com/api``. This module uses two of those endpoints politely (slow
rate limit, cache):

- ``GET /api/decks/v3/``   deck search (name, commanderName, cardName, deckFormat,
  ownerUsername, edhBracket, colors/andcolors, orderBy, page, pageSize)
- ``GET /api/decks/<id>/`` one public deck with its full card list

Treat it as best-effort: response shapes can change without notice, and a
public app built on this should ask Archidekt first.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

from .http import HttpClient

BASE = "https://archidekt.com/api"
SEARCH_TTL = 6 * 3600
DECK_TTL = 6 * 3600

FORMATS = {
    1: "Standard", 2: "Modern", 3: "Commander", 4: "Legacy", 5: "Vintage", 6: "Pauper",
    7: "Custom", 8: "Frontier", 9: "Future Standard", 10: "Penny Dreadful",
    11: "1v1 Commander", 12: "Duel Commander", 13: "Brawl", 14: "Oathbreaker",
    15: "Pioneer", 16: "Historic", 17: "Pauper EDH", 18: "Alchemy", 19: "Explorer",
    20: "Historic Brawl", 21: "Gladiator", 22: "Premodern", 23: "PreDH", 24: "Timeless",
}
FORMAT_IDS = {v.lower(): k for k, v in FORMATS.items()}
FORMAT_IDS.update({"edh": 3, "cedh": 3, "duel": 12})

COLOR_NAMES = {"w": "White", "u": "Blue", "b": "Black", "r": "Red", "g": "Green", "c": "Colorless"}
ORDERINGS = {
    "views": "-viewCount",
    "newest": "-createdAt",
    "updated": "-updatedAt",
    "name": "name",
}
BASIC_LANDS = {
    "plains", "island", "swamp", "mountain", "forest", "wastes",
    "snow-covered plains", "snow-covered island", "snow-covered swamp",
    "snow-covered mountain", "snow-covered forest",
}
# Archidekt's default non-deck boards. Deck JSON also flags these with includedInDeck=false.
OUT_OF_DECK = {"maybeboard", "sideboard", "considering", "tokens & extras", "tokens"}

_DECK_URL = re.compile(r"archidekt\.com/(?:api/)?decks/(\d+)", re.IGNORECASE)


def parse_deck_id(value: str | int) -> int | None:
    """Accept 12345, '12345' or any archidekt.com/decks/12345/... URL."""
    if isinstance(value, int):
        return value
    value = value.strip()
    if value.isdigit():
        return int(value)
    m = _DECK_URL.search(value)
    return int(m.group(1)) if m else None


def format_id(fmt: str | int | None) -> int | None:
    if fmt is None or fmt == "":
        return None
    if isinstance(fmt, int) or str(fmt).isdigit():
        return int(fmt)
    fid = FORMAT_IDS.get(str(fmt).strip().lower())
    if fid is None:
        raise ValueError(f"Unknown format {fmt!r}. Known: {', '.join(sorted(set(FORMAT_IDS)))}")
    return fid


def color_param(colors: str | None) -> str | None:
    """'wub' -> 'White,Blue,Black'. Also accepts 'White,Blue'."""
    if not colors:
        return None
    if "," in colors or len(colors) > 6:
        return ",".join(c.strip().capitalize() for c in colors.split(",") if c.strip())
    out = []
    for ch in colors.lower():
        if ch not in COLOR_NAMES:
            raise ValueError(f"Unknown colour letter {ch!r}; use letters from WUBRGC.")
        out.append(COLOR_NAMES[ch])
    return ",".join(dict.fromkeys(out))


def deck_url(deck_id: Any) -> str:
    return f"https://archidekt.com/decks/{deck_id}"


def _color_letters(colors: Any) -> str | None:
    if not isinstance(colors, dict):
        return None
    letters = "".join(c for c in "WUBRG" if (colors.get(c) or 0) > 0)
    return letters or "C"


def summarize_search_result(d: dict[str, Any]) -> dict[str, Any]:
    owner = d.get("owner") or {}
    fmt = d.get("deckFormat")
    out = {
        "id": d.get("id"),
        "name": d.get("name"),
        "url": deck_url(d.get("id")),
        "owner": owner.get("username") if isinstance(owner, dict) else owner,
        "format": FORMATS.get(fmt, fmt),
        "size": d.get("size"),
        "colors": _color_letters(d.get("colors")),
        "bracket": d.get("edhBracket"),
        "views": d.get("viewCount"),
        "tags": [t.get("name") if isinstance(t, dict) else t for t in (d.get("tags") or [])] or None,
        "theorycrafted": d.get("theorycrafted") or None,
        "updated": (d.get("updatedAt") or "")[:10] or None,
    }
    return {k: v for k, v in out.items() if v not in (None, "", [])}


# --------------------------------------------------------------------------- deck parsing


def _card_name(entry: dict[str, Any]) -> str | None:
    card = entry.get("card") or {}
    oracle = card.get("oracleCard") or {}
    return oracle.get("name") or card.get("name") or entry.get("name")


def _entry_categories(entry: dict[str, Any]) -> list[str]:
    cats = entry.get("categories") or []
    return [c.get("name") if isinstance(c, dict) else c for c in cats if c]


def _price(entry: dict[str, Any]) -> float | None:
    prices = (entry.get("card") or {}).get("prices") or {}
    for key in ("tcg", "ck", "cm"):
        val = prices.get(key)
        try:
            if val not in (None, "", 0, "0"):
                return float(val)
        except (TypeError, ValueError):
            continue
    return None


def parse_deck(deck: dict[str, Any]) -> dict[str, Any]:
    """Split an Archidekt deck JSON into commanders / main / out-of-deck boards."""
    excluded = {c.lower() for c in OUT_OF_DECK}
    commander_cats = {"commander", "commanders"}
    for cat in deck.get("categories") or []:
        name = (cat.get("name") or "").lower()
        if cat.get("includedInDeck") is False:
            excluded.add(name)
        elif name in excluded:  # user re-included a default board
            excluded.discard(name)

    commanders: list[dict[str, Any]] = []
    main: list[dict[str, Any]] = []
    other: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in deck.get("cards") or []:
        if entry.get("deletedAt"):
            continue
        name = _card_name(entry)
        if not name:
            continue
        cats = _entry_categories(entry)
        # Archidekt puts a card in the board of its first (primary) category.
        primary = (cats[0] if cats else "").lower()
        oracle = (entry.get("card") or {}).get("oracleCard") or {}
        row = {
            "name": name,
            "qty": entry.get("quantity") or 1,
            "categories": cats,
            "cmc": oracle.get("cmc"),
            "types": oracle.get("types"),
            "usd": _price(entry),
        }
        if primary in commander_cats or any(c.lower() in commander_cats for c in cats):
            commanders.append(row)
        elif primary in excluded:
            other[cats[0]].append(row)
        else:
            main.append(row)
    return {"commanders": commanders, "main": main, "other_boards": dict(other)}


def to_decklist(parsed: dict[str, Any]) -> str:
    """Arena-style text that analyze_deck / find_combos / price_decklist accept."""
    lines = []
    if parsed["commanders"]:
        lines.append("Commander")
        lines += [f"{c['qty']} {c['name']}" for c in parsed["commanders"]]
        lines.append("")
        lines.append("Deck")
    lines += [f"{c['qty']} {c['name']}" for c in parsed["main"]]
    return "\n".join(lines)


class Archidekt:
    def __init__(self, http: HttpClient):
        self.http = http

    async def search(
        self,
        *,
        name: str | None = None,
        commander: str | None = None,
        card: str | None = None,
        fmt: str | int | None = None,
        owner: str | None = None,
        colors: str | None = None,
        exact_colors: bool = False,
        bracket: int | None = None,
        order: str = "views",
        page: int = 1,
        limit: int = 20,
    ) -> dict[str, Any]:
        fid = format_id(fmt)
        params: dict[str, Any] = {
            "orderBy": ORDERINGS.get(order, order),
            "page": max(1, page),
            "pageSize": max(1, min(limit, 50)),
        }
        if name:
            params["name"] = name
        if commander:
            params["commanderName"] = commander
        if card:
            params["cardName"] = card
        if fid is not None:
            params["deckFormat"] = fid
        if owner:
            params["ownerUsername"] = owner
        cp = color_param(colors)
        if cp:
            params["colors"] = cp
            if exact_colors:
                params["andcolors"] = "true"
        if bracket:
            params["edhBracket"] = bracket
        data = await self.http.get(f"{BASE}/decks/v3/", params=params, ttl=SEARCH_TTL)
        results = data.get("results") or []
        # The endpoint sometimes ignores filters it doesn't know; enforce the ones we can check.
        if fid is not None:
            results = [r for r in results if r.get("deckFormat") in (None, fid)]
        results = [r for r in results if not r.get("private")]
        return {
            "total_matches": data.get("count"),
            "page": params["page"],
            "has_more": bool(data.get("next")),
            "decks": [summarize_search_result(r) for r in results[: params["pageSize"]]],
        }

    async def deck(self, deck_id: int) -> dict[str, Any] | None:
        return await self.http.get(f"{BASE}/decks/{deck_id}/", ttl=DECK_TTL, allow_404=True)

    async def deck_summary(self, deck_id: int, *, include_cards: bool = True) -> dict[str, Any]:
        raw = await self.deck(deck_id)
        if raw is None:
            return {"error": f"Archidekt deck {deck_id} not found (it may be private or deleted)."}
        parsed = parse_deck(raw)
        owner = raw.get("owner") or {}
        fmt = raw.get("deckFormat")
        by_category: dict[str, int] = Counter()
        for c in parsed["main"] + parsed["commanders"]:
            for cat in c["categories"] or ["Uncategorized"]:
                by_category[cat] += c["qty"]
        priced = [c for c in parsed["commanders"] + parsed["main"] if c["usd"] is not None]
        out: dict[str, Any] = {
            "id": raw.get("id", deck_id),
            "name": raw.get("name"),
            "url": deck_url(raw.get("id", deck_id)),
            "owner": owner.get("username") if isinstance(owner, dict) else owner,
            "format": FORMATS.get(fmt, fmt),
            "bracket": raw.get("edhBracket"),
            "views": raw.get("viewCount"),
            "created": (raw.get("createdAt") or "")[:10] or None,
            "updated": (raw.get("updatedAt") or "")[:10] or None,
            "description": (raw.get("description") or "")[:1500] or None,
            "commanders": [c["name"] for c in parsed["commanders"]],
            "card_count": sum(c["qty"] for c in parsed["commanders"] + parsed["main"]),
            "category_counts": dict(sorted(by_category.items(), key=lambda kv: -kv[1])),
            "approx_price_usd": round(sum(c["usd"] * c["qty"] for c in priced), 2) if priced else None,
            "other_boards": {k: sum(c["qty"] for c in v) for k, v in parsed["other_boards"].items()} or None,
        }
        if include_cards:
            grouped: dict[str, list[str]] = defaultdict(list)
            for c in parsed["main"]:
                label = f"{c['qty']} {c['name']}" if c["qty"] > 1 else c["name"]
                grouped[c["categories"][0] if c["categories"] else "Uncategorized"].append(label)
            out["cards_by_category"] = dict(grouped)
            out["decklist"] = to_decklist(parsed)
        out["source"] = "Archidekt (unofficial JSON; best-effort)"
        return {k: v for k, v in out.items() if v not in (None, "", [], {})}

    async def popular_cards(
        self,
        commander: str,
        *,
        decks: int = 15,
        order: str = "views",
        bracket: int | None = None,
        exclude: set[str] | None = None,
        include_basics: bool = False,
        top: int = 60,
    ) -> dict[str, Any]:
        """Fetch the top Archidekt decks for a commander and count how often each card appears."""
        found = await self.search(commander=commander, fmt=3, order=order, bracket=bracket, limit=min(50, decks * 2))
        candidates = found["decks"]
        cmd_lower = commander.lower()
        counts: Counter[str] = Counter()
        cat_votes: dict[str, Counter[str]] = defaultdict(Counter)
        used: list[dict[str, Any]] = []
        skipped: list[str] = []
        for d in candidates:
            if len(used) >= decks:
                break
            raw = await self.deck(d["id"])
            if raw is None:
                skipped.append(d.get("name") or str(d["id"]))
                continue
            parsed = parse_deck(raw)
            cmd_names = [c["name"] for c in parsed["commanders"]]
            # Search matches commander names loosely; keep decks that really lead with this commander.
            if cmd_names and not any(cmd_lower in n.lower() for n in cmd_names):
                skipped.append(d.get("name") or str(d["id"]))
                continue
            if len(parsed["main"]) < 40:  # skip stubs and unfinished lists
                skipped.append(d.get("name") or str(d["id"]))
                continue
            used.append({"name": d.get("name"), "url": d.get("url"), "views": d.get("views"), "commanders": cmd_names})
            seen = set()
            for c in parsed["main"]:
                key = c["name"]
                if key in seen:
                    continue
                seen.add(key)
                counts[key] += 1
                for cat in c["categories"]:
                    cat_votes[key][cat] += 1
        if not used:
            return {
                "error": f"No usable Archidekt Commander decks found for {commander!r}.",
                "search_matches": found.get("total_matches"),
            }
        exclude_l = {x.lower() for x in (exclude or set())}
        n = len(used)
        rows = []
        for name, k in counts.most_common():
            low = name.lower()
            if low in exclude_l or (not include_basics and low in BASIC_LANDS):
                continue
            rows.append({
                "name": name,
                "decks": k,
                "inclusion_pct": round(100 * k / n, 1),
                "usual_category": cat_votes[name].most_common(1)[0][0] if cat_votes[name] else None,
            })
            if len(rows) >= top:
                break
        return {
            "commander": commander,
            "decks_sampled": n,
            "sampled_decks": used,
            "skipped_decks": skipped or None,
            "cards": rows,
            "excluded_cards_already_in_deck": len(exclude_l) or None,
            "note": "Inclusion % is across the sampled public Archidekt decks (most viewed first by default), "
                    "a smaller and different sample than EDHREC.",
            "source": "Archidekt (unofficial JSON; best-effort)",
        }
