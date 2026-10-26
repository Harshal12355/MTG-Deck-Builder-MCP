"""MCP tool implementations."""

from __future__ import annotations

from typing import Any, Literal

from .. import wiring
from ..http import ApiError


def _clients():
    return wiring.clients()


def _error(exc: ApiError) -> dict[str, Any]:
    return wiring.api_error(exc)


async def _resolve_deck(decklist: str, commanders: list[str] | None):
    return await wiring.resolve_deck(decklist, commanders)


def _archidekt():
    return wiring.archidekt()


from ..analysis import card_roles
from ..forge import fetch_forge_tags
from ..scryfall import summarize_card


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


async def get_card(
    name: str,
    set_code: str | None = None,
    exact: bool = False,
    include_forge_tags: bool = False,
) -> dict[str, Any]:
    """Look up one card by name (fuzzy by default, so misspellings and partial names work).

    Returns oracle text, types, colours, legalities, price and the card's heuristic deck roles.
    Pass `include_forge_tags=True` to also fetch Card-Forge's human-written `DeckHas`, `DeckNeeds`,
    `DeckHints`, and AST ability/trigger tags.
    """
    scryfall, _, _ = _clients()
    try:
        card = await scryfall.named(name, fuzzy=not exact, set_code=set_code)
    except ApiError as exc:
        return _error(exc)
    out = summarize_card(card)
    out["roles"] = card_roles(card) or None
    if include_forge_tags:
        ftags = await fetch_forge_tags(wiring.http_client(), card.get("name", name))
        card["forge_tags"] = ftags
        out["forge_tags"] = ftags
    return out


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


async def autocomplete_card_name(partial: str) -> dict[str, Any]:
    """Suggest up to 20 real card names for a partial or misspelled name."""
    scryfall, _, _ = _clients()
    try:
        return {"suggestions": await scryfall.autocomplete(partial)}
    except ApiError as exc:
        return _error(exc)


async def random_card(query: str | None = None) -> dict[str, Any]:
    """A random card, optionally restricted by a Scryfall query (e.g. `is:commander id:ur`)."""
    scryfall, _, _ = _clients()
    try:
        return summarize_card(await scryfall.random(query))
    except ApiError as exc:
        return _error(exc)

def register(mcp) -> None:
    mcp.tool()(search_cards)
    mcp.tool()(get_card)
    mcp.tool()(get_card_rulings)
    mcp.tool()(get_card_printings)
    mcp.tool()(autocomplete_card_name)
    mcp.tool()(random_card)
