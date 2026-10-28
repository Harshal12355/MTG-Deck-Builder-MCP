"""MCP server exposing Magic: The Gathering deckbuilding tools.

Run:
    mtg-mcp                  # stdio (Claude Desktop, Claude Code, etc.)
    mtg-mcp --http           # streamable HTTP on 127.0.0.1:8000/mcp
"""

from __future__ import annotations

import argparse

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from . import wiring
from .skills import register_prompts
from .tools import register_tools

# Re-export tool callables for tests (implementation lives in tools/*.py).
from .tools import (  # noqa: F401
    analyze_deck,
    analyze_mana_base,
    archidekt_get_deck,
    archidekt_popular_cards,
    archidekt_search_decks,
    autocomplete_card_name,
    check_pod,
    compare_decks,
    deckbuilding_principles,
    deckbuilding_template,
    edhrec_card,
    edhrec_recommendations,
    find_combos,
    find_tokens,
    get_card,
    get_card_printings,
    get_card_rulings,
    get_skill,
    moxfield_import_user,
    price_decklist,
    random_card,
    reference_card,
    reference_cards,
    reference_compare,
    reference_deck,
    reference_library,
    reference_principles,
    search_cards,
    search_combos,
    search_lands,
    simulate_deck,
)

set_http_client = wiring.set_http_client

INSTRUCTIONS = """\
Magic: The Gathering deckbuilding MCP. Never answer card text from memory; look it up.

Cards (Scryfall + Card-Forge):
- search_cards: Scryfall syntax (`id<=bg t:creature o:"sacrifice" usd<3 f:commander`).
- get_card: oracle text, legality, USD price, roles, and `include_forge_tags=True` (`DeckHas`/`DeckNeeds`/AST).
- get_card_rulings: official Gatherer rulings. get_card_printings: printings sorted cheapest first.
- autocomplete_card_name: partial/misspelled names. random_card: random card or commander ideas.

Deck Analysis, Mana & Simulation:
- analyze_deck: legality, WotC Bracket 1-5, 0-10 Power Score, 3-School Score, 10-axis synergy, curve, roles, price (`include_combos=True` runs Spellbook concurrently).
- analyze_mana_base: Karsten 90% cast rates, tipping point, and 0-100 grade. search_lands: 24 land cycles by speed and budget.
- price_decklist: USD/EUR totals and `budget_target` cuts. find_tokens: token checklist and doublers.
- compare_decks: before/after upgrade deltas. check_pod: 2-4 deck Rule 0 table balance.
- simulate_deck: Monte Carlo goldfish (`win_lines`, `mulligan_targets`, `track_card_impact=True`, fixed `seed` for A/B).
- deckbuilding_template: Command Zone 38L/10R/12D/12T/6M/30P targets (customizable). deckbuilding_principles: ~$100 Bracket 4 rules.

Combos, EDHREC & Archidekt:
- find_combos: in-deck and 1-card-away combos. search_combos: Commander Spellbook search.
- edhrec_recommendations: commander synergy/budget recs. edhrec_card: top commanders and pairings for one card.
- archidekt_search_decks, archidekt_get_deck, archidekt_popular_cards: public decks and meta inclusion rates.

Reference Library & Deckbuilding Skills:
- Tested ~$100 Bracket 4 lists (NeRo): reference_library, reference_principles, reference_cards, reference_card, reference_deck, reference_compare, moxfield_import_user.
- Skills (also MCP prompts): call get_skill and follow it (`deck-plan` for a new commander, `deck-upgrade` for a pasted list — lock the goal, the win, and the budget before a new list — then `nero-build` or `nero-tune`, running NeRo + Defcat + Based 3x33 passes through `moxfield-primer`).
"""

mcp = FastMCP("mtg-deckbuilder", instructions=INSTRUCTIONS)

register_prompts(mcp)
register_tools(mcp)


def main() -> None:
    parser = argparse.ArgumentParser(description="MTG deckbuilder MCP server")
    parser.add_argument("--http", action="store_true", help="Serve streamable HTTP instead of stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--allowed-host", action="append", default=[],
                        help="Extra Host header to accept, e.g. mtg.example.com:* (repeatable)")
    args = parser.parse_args()
    if args.http:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        if args.allowed_host:
            mcp.settings.transport_security = TransportSecuritySettings(
                enable_dns_rebinding_protection=True,
                allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*", *args.allowed_host],
                allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"],
            )
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
