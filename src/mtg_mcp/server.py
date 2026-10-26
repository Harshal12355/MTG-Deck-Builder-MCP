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
Tools for Magic: The Gathering questions and deckbuilding.

- Card facts, rules text, prices, and Card-Forge AI synergy tags: search_cards / get_card. Never answer card text from memory; look it up.
  Pass `include_forge_tags=True` to `get_card` on the commander or key synergy pieces to inspect Card-Forge's human-written
  `DeckHas`, `DeckNeeds`, `DeckHints`, `abilities`, `triggers`, and `sacrifice_costs`.
- Rules questions about a card: get_card_rulings. Cheapest printings: get_card_printings.
- A pasted decklist (Moxfield, Arena, Archidekt, MTGO or plain text): analyze_deck(include_combos=True) first (reports WotC Bracket 1-5,
  0-10 Power Score, 3-School Score, and 10-axis Enabler x Payoff synergy; include_combos=True concurrently queries
  Commander Spellbook in one call), then price_decklist(budget_target=100), find_combos, analyze_mana_base, find_tokens, and edhrec_recommendations.
- Mana base, diffs, pod balance, and tokens: analyze_mana_base for Karsten 90% cast rates, tipping point, and 0-100 grade;
  search_lands for 24 land cycles by speed and budget; compare_decks for before/after upgrade deltas;
  check_pod for 2-4 deck Rule 0 table balance; find_tokens for token counts and doublers.
- search_cards uses Scryfall syntax, e.g. `id<=bg t:creature o:"sacrifice" usd<3 f:commander`.
  For Commander, restrict to the commander's colours with `id<=<colors>` and `f:commander`.
- Building or tuning a Commander deck: follow the deckbuilding template (call deckbuilding_template).
  By default: 38 lands, 10 ramp, 12 card advantage, 12 targeted disruption, 6 mass disruption, 30 plan cards.
  The targets add up to 108 for 99 slots, so about 9 cards should fill two roles.
  The player may change any of these numbers. Use their numbers for the rest of the conversation,
  passing them as `template` to deckbuilding_template and analyze_deck.
- For focused, high-power or budget (~$100) builds, also call deckbuilding_principles and follow it:
  engine commander, define the win line first, build backwards from the ideal turn, average mana value
  near or below 2.0, synergy over staples, 29-34 lands rather than a rigid template, and interaction
  that protects your own win first. Its build_process gives the order to build in: analyze what the
  commander really enables, choose the win condition, fill ramp/draw/interaction at higher-than-usual
  counts, then pick synergistic cards for every slot. Cut the enabler that does nothing the turn you cast it.
  Don't copy EDHREC lists wholesale.
- To test how a deck plays, call simulate_deck with its win lines (groups of card names), `track_card_impact=True`
  (single-card knockout attribution), and optional `mulligan_targets`. Compare runs before and after changes
  with the same `seed` rather than reading the numbers as win rates.
- Real decks people have built: archidekt_search_decks (by commander, card, name, owner, colours, bracket),
  archidekt_get_deck for one deck's full list (its `decklist` field can go straight into analyze_deck / find_combos),
  and archidekt_popular_cards to see what the most-viewed Archidekt decks for a commander actually run.
- Reference library (reference_library and reference_* tools): real, tested budget high-power decks from builders we learn from
  (first source: NeRo, ~$100 Bracket 4 / budget cEDH lists with primers). Use it when building or tuning:
  reference_library for an overview of builders and decks, reference_principles for the builder's principles, reference_cards for proven card choices by role / colour
  identity / price, reference_deck for a full list with its win lines (pass them to simulate_deck),
  reference_card to see how a card was used, and reference_compare to find proven staples a deck is missing.
  Library prices are capture-time snapshots; re-check with price_decklist. moxfield_import_user adds or refreshes a builder.
- Utility lookups: autocomplete_card_name for partial/misspelled names; random_card for random commander or card ideas;
  edhrec_card for top commanders and high-synergy pairings for a single card.
- Deckbuilding skills: call get_skill and follow what it returns.
  nero-build when there is a commander and no list. nero-tune when a decklist or a link is already here.
  All three schools run on the same list (NeRo + Defcat + Based 33-card). nero-read, then defcat-read, before naming cards.
  nero-lines for the win (one spell, a pile, or overlapping combos via search_combos).
  based-core locks the 33-card 1-game blueprint (1/3 of 99) and goldfishes that 33-card core first at low variance.
  nero-hunt for draw, ramp, interaction, then cards that also do the plan.
  defcat-turn rescores those cards for when in the turn they want to resolve.
  defcat-fuel only when defcat-read finds a mana-value bar (Rashmi, cascade, the first spell each turn).
  based-scale replicates the tested 33-card core two more times (33 x 3 = 99) with functional twins and zero 1/0/0 orphans.
  based-split deals an existing 99-card deck into 3 x 33 piles to expose uneven splits, 1/0/0 orphans, and slow value engines.
  nero-mana for a mana-base pass. nero-goldfish calls simulate_deck (on the 33-card core and the full 99). Do not stop a build or a tune before it, or before analyze_deck, price_decklist, and find_combos.
  moxfield-primer after the list is final: Moxfield `#tags` on every card plus a markdown primer to paste.
  The same text is available as MCP prompts under those names.
Prices are Scryfall's daily USD/EUR market prices. EDHREC and Archidekt data are best-effort.
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
