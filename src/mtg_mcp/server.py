"""MCP server exposing Magic: The Gathering deckbuilding tools.

Run:
    mtg-mcp                  # stdio (Claude Desktop, Claude Code, etc.)
    mtg-mcp --http           # streamable HTTP on 127.0.0.1:8000/mcp
"""

from __future__ import annotations

import argparse
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from .analysis import analyze, card_roles
from .decklist import ParsedDeck, parse_decklist
from .edhrec import Edhrec
from .http import ApiError, HttpClient
from .scryfall import Scryfall, price_usd, summarize_card
from .spellbook import Spellbook

INSTRUCTIONS = """\
Tools for Magic: The Gathering questions and deckbuilding.

- Card facts, rules text and prices: search_cards / get_card. Never answer card text from memory; look it up.
- Rules questions about a card: get_card_rulings.
- A pasted decklist (Moxfield, Arena, Archidekt, MTGO or plain text): analyze_deck first,
  then find_combos and edhrec_recommendations (pass the decklist so cards already in the deck are skipped).
- search_cards uses Scryfall syntax, e.g. `id<=bg t:creature o:"sacrifice" usd<3 f:commander`.
  For Commander, restrict to the commander's colours with `id<=<colors>` and `f:commander`.
Prices are Scryfall's daily USD market prices. EDHREC data is best-effort.
"""

mcp = FastMCP("mtg-deckbuilder", instructions=INSTRUCTIONS)

_http: HttpClient | None = None


def _clients() -> tuple[Scryfall, Spellbook, Edhrec]:
    global _http
    if _http is None:
        _http = HttpClient()
    return Scryfall(_http), Spellbook(_http), Edhrec(_http)


def set_http_client(http: HttpClient) -> None:
    """Swap the shared HTTP client (used by tests)."""
    global _http
    _http = http


def _error(exc: ApiError) -> dict[str, Any]:
    return {"error": str(exc), "status": exc.status}


async def _resolve_deck(decklist: str, commanders: list[str] | None) -> tuple[ParsedDeck, dict[str, dict[str, Any]], list[str]]:
    scryfall, _, _ = _clients()
    deck = parse_decklist(decklist, commanders)
    cards, not_found = await scryfall.collection(e.name for e in deck.commanders + deck.main + deck.sideboard)
    return deck, cards, not_found


# --------------------------------------------------------------------------- cards


@mcp.tool()
async def search_cards(
    query: str,
    order: Literal["edhrec", "name", "cmc", "usd", "released", "rarity", "power", "toughness"] = "edhrec",
    direction: Literal["auto", "asc", "desc"] = "auto",
    limit: int = 20,
    detail: Literal["brief", "full"] = "brief",
) -> dict[str, Any]:
    """Search cards with full Scryfall syntax (https://scryfall.com/docs/syntax).

    Examples: `t:legendary t:creature id:bg`, `o:"draw a card" id<=u cmc<=2 f:commander`,
    `otag:ramp id<=g usd<1`, `is:commander keyword:partner`.
    order="edhrec" sorts by popularity in Commander. detail="full" includes oracle text.
    """
    scryfall, _, _ = _clients()
    try:
        result = await scryfall.search(query, order=order, direction=direction, limit=max(1, min(limit, 100)))
    except ApiError as exc:
        return _error(exc)
    return {
        "query": query,
        "total_matches": result["total_cards"],
        "returned": len(result["cards"]),
        "cards": [summarize_card(c, detail) for c in result["cards"]],
        "warnings": result.get("warnings"),
    }


@mcp.tool()
async def get_card(name: str, set_code: str | None = None, exact: bool = False) -> dict[str, Any]:
    """Look up one card by name (fuzzy by default, so misspellings and partial names work).

    Returns oracle text, types, colours, legalities, price and the card's heuristic deck roles.
    """
    scryfall, _, _ = _clients()
    try:
        card = await scryfall.named(name, fuzzy=not exact, set_code=set_code)
    except ApiError as exc:
        return _error(exc)
    out = summarize_card(card)
    out["roles"] = card_roles(card) or None
    return out


@mcp.tool()
async def get_card_rulings(name: str) -> dict[str, Any]:
    """Official rulings and Gatherer notes for a card, plus its oracle text for context."""
    scryfall, _, _ = _clients()
    try:
        card = await scryfall.named(name)
        rulings = await scryfall.rulings(card)
    except ApiError as exc:
        return _error(exc)
    return {
        "card": card.get("name"),
        "oracle_text": summarize_card(card).get("oracle_text"),
        "rulings": [{"date": r.get("published_at"), "source": r.get("source"), "text": r.get("comment")} for r in rulings],
    }


@mcp.tool()
async def get_card_printings(name: str, limit: int = 15) -> dict[str, Any]:
    """Every printing of a card, cheapest first, with set and USD prices. Useful for budget builds."""
    scryfall, _, _ = _clients()
    try:
        card = await scryfall.named(name)
        prints = await scryfall.printings(card, limit=max(1, min(limit, 100)))
    except ApiError as exc:
        return _error(exc)
    return {
        "card": card.get("name"),
        "printings": [
            {
                "set": p.get("set"),
                "set_name": p.get("set_name"),
                "collector_number": p.get("collector_number"),
                "released": p.get("released_at"),
                "usd": (p.get("prices") or {}).get("usd"),
                "usd_foil": (p.get("prices") or {}).get("usd_foil"),
                "scryfall_uri": p.get("scryfall_uri"),
            }
            for p in prints
        ],
    }


@mcp.tool()
async def autocomplete_card_name(partial: str) -> dict[str, Any]:
    """Suggest up to 20 real card names for a partial or misspelled name."""
    scryfall, _, _ = _clients()
    try:
        return {"suggestions": await scryfall.autocomplete(partial)}
    except ApiError as exc:
        return _error(exc)


@mcp.tool()
async def random_card(query: str | None = None) -> dict[str, Any]:
    """A random card, optionally restricted by a Scryfall query (e.g. `is:commander id:ur`)."""
    scryfall, _, _ = _clients()
    try:
        return summarize_card(await scryfall.random(query))
    except ApiError as exc:
        return _error(exc)


# --------------------------------------------------------------------------- decks


@mcp.tool()
async def analyze_deck(
    decklist: str,
    format: str = "commander",
    commanders: list[str] | None = None,
    budget_per_card: float | None = None,
) -> dict[str, Any]:
    """Analyse a pasted decklist (Moxfield, Arena, Archidekt, MTGO or plain `1 Card Name` lines).

    Reports legality for the format (size, copies, colour identity, bans), mana curve,
    colour pips vs land sources, card roles (ramp, draw, removal, wipes, tutors...),
    gaps against a typical Commander template, Game Changers, and total price.
    Pass `commanders` if the list doesn't mark them. `budget_per_card` flags cards above that USD price.
    """
    try:
        deck, cards, not_found = await _resolve_deck(decklist, commanders)
    except ApiError as exc:
        return _error(exc)
    if not deck.playing:
        return {"error": "Couldn't find any cards in that decklist.", "unparsed_lines": deck.unparsed_lines[:10]}
    result = analyze(deck, cards, fmt=format, budget_per_card=budget_per_card)
    result["cards_not_found"] = sorted(set(result["cards_not_found"]) | set(not_found)) or None
    if deck.unparsed_lines:
        result["unparsed_lines"] = deck.unparsed_lines[:20]
    return result


@mcp.tool()
async def find_combos(decklist: str, commanders: list[str] | None = None, include_steps: bool = True) -> dict[str, Any]:
    """Find combos already in a deck and combos that are one card away (Commander Spellbook).

    Also lists combos that would work with a different commander or by adding colours.
    """
    _, spellbook, _ = _clients()
    deck = parse_decklist(decklist, commanders)
    if not deck.playing:
        return {"error": "Couldn't find any cards in that decklist."}
    try:
        return await spellbook.find_my_combos(deck, include_steps=include_steps)
    except ApiError as exc:
        return _error(exc)


@mcp.tool()
async def search_combos(query: str, limit: int = 10) -> dict[str, Any]:
    """Search Commander Spellbook combos, most popular first.

    Query syntax examples: `card:"Thassa's Oracle"`, `result:"infinite mana" id<=bg`, `cards=2 result:"win the game"`.
    """
    _, spellbook, _ = _clients()
    try:
        return await spellbook.search(query, limit=max(1, min(limit, 50)))
    except ApiError as exc:
        return _error(exc)


@mcp.tool()
async def edhrec_recommendations(
    commander: str,
    partner: str | None = None,
    theme: str | None = None,
    budget: Literal["any", "budget", "expensive"] = "any",
    decklist: str | None = None,
    per_list: int = 15,
    categories: list[str] | None = None,
) -> dict[str, Any]:
    """EDHREC recommendations for a commander: high-synergy cards, top cards, and per-type lists.

    - theme: an EDHREC theme like "tokens", "+1/+1 counters", "aristocrats" (see `themes` in the result).
    - budget: "budget" or "expensive" EDHREC variants.
    - decklist: if given, cards already in the deck are removed so results are suggested *adds*.
    - categories: restrict to list tags such as ["highsynergycards", "topcards", "creatures", "instants"].
    Each card shows inclusion % (share of this commander's decks running it) and synergy % (how much
    more often it appears here than in other decks of these colours).
    """
    scryfall, _, edhrec = _clients()
    names = [commander] + ([partner] if partner else [])
    try:
        # Normalise names through Scryfall so slugs match (fixes typos/partial names).
        resolved = []
        for n in names:
            card = await scryfall.named(n)
            resolved.append(card.get("name", n))
        exclude: set[str] = set()
        if decklist:
            deck = parse_decklist(decklist)
            exclude = {e.name for e in deck.playing}
        return await edhrec.commander(
            resolved,
            theme=theme,
            budget=None if budget == "any" else budget,
            exclude=exclude,
            per_list=max(1, min(per_list, 50)),
            categories=categories,
        )
    except ApiError as exc:
        return _error(exc)


@mcp.tool()
async def edhrec_card(name: str) -> dict[str, Any]:
    """EDHREC data for a card: the commanders that play it most and cards commonly played with it."""
    scryfall, _, edhrec = _clients()
    try:
        card = await scryfall.named(name)
        return await edhrec.card(card.get("name", name))
    except ApiError as exc:
        return _error(exc)


@mcp.tool()
async def price_decklist(decklist: str) -> dict[str, Any]:
    """Quick price check of a decklist: per-card USD price and total, most expensive first."""
    scryfall, _, _ = _clients()
    deck = parse_decklist(decklist)
    entries = deck.playing + deck.sideboard
    try:
        cards, not_found = await scryfall.collection(e.name for e in entries)
    except ApiError as exc:
        return _error(exc)
    rows = []
    for e in entries:
        c = cards.get(e.name.lower())
        if c is None:
            continue
        p = price_usd(c)
        rows.append({"card": c.get("name"), "qty": e.quantity, "usd_each": p, "usd_total": round(p * e.quantity, 2) if p is not None else None})
    rows.sort(key=lambda r: -(r["usd_total"] or 0))
    return {
        "total_usd": round(sum(r["usd_total"] or 0 for r in rows), 2),
        "cards": rows,
        "no_price_listed": [r["card"] for r in rows if r["usd_each"] is None] or None,
        "cards_not_found": not_found or None,
    }


# --------------------------------------------------------------------------- entry point


def main() -> None:
    parser = argparse.ArgumentParser(description="MTG deckbuilder MCP server")
    parser.add_argument("--http", action="store_true", help="Serve streamable HTTP instead of stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.http:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
