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


from ..decklist import parse_decklist


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


async def search_combos(query: str, limit: int = 10) -> dict[str, Any]:
    """Search Commander Spellbook combos, most popular first.

    Query syntax examples: `card:"Thassa's Oracle"`, `result:"infinite mana" id<=bg`, `cards=2 result:"win the game"`.
    """
    _, spellbook, _ = _clients()
    try:
        return await spellbook.search(query, limit=max(1, min(limit, 50)))
    except ApiError as exc:
        return _error(exc)


def register(mcp) -> None:
    mcp.tool()(find_combos)
    mcp.tool()(search_combos)
