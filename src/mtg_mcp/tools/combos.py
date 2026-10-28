"""Commander Spellbook combo MCP tools."""

from __future__ import annotations

from typing import Any

from .. import wiring
from ..decklist import parse_decklist
from ..http import ApiError


async def find_combos(decklist: str, commanders: list[str] | None = None, include_steps: bool = True) -> dict[str, Any]:
    """Find combos already in a deck and combos that are one card away (Commander Spellbook).

    Also lists combos that would work with a different commander or by adding colours.
    """
    _, spellbook, _ = wiring.clients()
    deck = parse_decklist(decklist, commanders)
    if not deck.playing:
        return {"error": "Couldn't find any cards in that decklist."}
    try:
        return await spellbook.find_my_combos(deck, include_steps=include_steps)
    except ApiError as exc:
        return wiring.api_error(exc)


async def search_combos(query: str, limit: int = 10) -> dict[str, Any]:
    """Search Commander Spellbook combos, most popular first.

    Query syntax examples: `card:"Thassa's Oracle"`, `result:"infinite mana" id<=bg`, `cards=2 result:"win the game"`.
    """
    _, spellbook, _ = wiring.clients()
    try:
        return await spellbook.search(query, limit=max(1, min(limit, 50)))
    except ApiError as exc:
        return wiring.api_error(exc)


def register(mcp) -> None:
    mcp.tool()(find_combos)
    mcp.tool()(search_combos)
