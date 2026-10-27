"""Archidekt deck search and inspection MCP tools."""

from __future__ import annotations

from typing import Any, Literal

from .. import wiring
from ..archidekt import parse_deck_id
from ..decklist import parse_decklist
from ..http import ApiError


async def archidekt_search_decks(
    commander: str | None = None,
    card: str | None = None,
    name: str | None = None,
    format: str | None = "commander",
    owner: str | None = None,
    colors: str | None = None,
    exact_colors: bool = False,
    bracket: int | None = None,
    order: Literal["views", "newest", "updated", "name"] = "views",
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """Search public decks on Archidekt.

    - commander: commander name (resolved through Scryfall first, so partial names work).
    - card: decks that include this card. name: text in the deck title. owner: Archidekt username.
    - format: "commander" (default), "modern", "standard", "pauper", "brawl", ... or None for any format.
    - colors: colour letters like "bg"; exact_colors=True requires all of them.
    - bracket: Commander bracket 1-5. order: "views" (most viewed), "newest", "updated" or "name".
    Returns deck ids and URLs; pass one to archidekt_get_deck for the full list.
    """
    scryfall, _, _ = wiring.clients()
    try:
        if commander:
            commander = (await scryfall.named(commander)).get("name", commander)
        if card:
            card = (await scryfall.named(card)).get("name", card)
        return await wiring.archidekt().search(
            name=name, commander=commander, card=card, fmt=format, owner=owner, colors=colors,
            exact_colors=exact_colors, bracket=bracket, order=order, page=page, limit=limit,
        )
    except ValueError as exc:
        return {"error": str(exc)}
    except ApiError as exc:
        return wiring.api_error(exc)


async def archidekt_get_deck(deck: str, include_cards: bool = True) -> dict[str, Any]:
    """One public Archidekt deck by id or URL (e.g. https://archidekt.com/decks/123456/my-deck).

    Returns commanders, the builder's categories with card counts (Ramp, Draw, Removal...),
    cards grouped by category, approximate price, description, and a plain `decklist`
    you can pass straight to analyze_deck, find_combos or price_decklist.
    """
    deck_id = parse_deck_id(deck)
    if deck_id is None:
        return {"error": f"Couldn't find an Archidekt deck id in {deck!r}."}
    try:
        return await wiring.archidekt().deck_summary(deck_id, include_cards=include_cards)
    except ApiError as exc:
        return wiring.api_error(exc)


async def archidekt_popular_cards(
    commander: str,
    decks: int = 15,
    order: Literal["views", "newest", "updated"] = "views",
    bracket: int | None = None,
    decklist: str | None = None,
    include_basics: bool = False,
    top: int = 60,
) -> dict[str, Any]:
    """Scour the top public Archidekt decks for a commander and report how often each card appears.

    - decks: how many decks to sample (1-30; each one is a separate request, about 1 s apiece).
    - order: sample the most viewed ("views"), newest or most recently updated decks.
    - bracket: only decks tagged with this Commander bracket (1-5).
    - decklist: if given, cards already in it are left out, so results are suggested adds.
    Each card shows inclusion % across the sample and the category builders most often file it under.
    A complement to edhrec_recommendations: smaller sample, but real, recently edited lists.
    """
    scryfall, _, _ = wiring.clients()
    try:
        resolved = (await scryfall.named(commander)).get("name", commander)
        exclude: set[str] = set()
        if decklist:
            exclude = {e.name for e in parse_decklist(decklist).playing}
        return await wiring.archidekt().popular_cards(
            resolved, decks=max(1, min(decks, 30)), order=order, bracket=bracket,
            exclude=exclude, include_basics=include_basics, top=max(1, min(top, 200)),
        )
    except ApiError as exc:
        return wiring.api_error(exc)


def register(mcp) -> None:
    mcp.tool()(archidekt_search_decks)
    mcp.tool()(archidekt_get_deck)
    mcp.tool()(archidekt_popular_cards)
