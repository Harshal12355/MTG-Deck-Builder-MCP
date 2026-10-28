"""EDHREC recommendation MCP tools."""

from __future__ import annotations

from typing import Any, Literal

from .. import wiring
from ..decklist import parse_decklist
from ..http import ApiError


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
    scryfall, _, edhrec = wiring.clients()
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
        return wiring.api_error(exc)


async def edhrec_card(name: str) -> dict[str, Any]:
    """EDHREC data for a card: the commanders that play it most and cards commonly played with it."""
    scryfall, _, edhrec = wiring.clients()
    try:
        card = await scryfall.named(name)
        return await edhrec.card(card.get("name", name))
    except ApiError as exc:
        return wiring.api_error(exc)


def register(mcp) -> None:
    mcp.tool()(edhrec_recommendations)
    mcp.tool()(edhrec_card)
