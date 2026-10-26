"""Register all MCP tool groups."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import archidekt_tools, cards, combos, deck, edhrec_tools, reference, skills_tool


def register_tools(mcp: FastMCP) -> None:
    cards.register(mcp)
    deck.register(mcp)
    combos.register(mcp)
    edhrec_tools.register(mcp)
    archidekt_tools.register(mcp)
    reference.register(mcp)
    skills_tool.register(mcp)


# Re-export tool callables for tests and direct invocation.
from .cards import (  # noqa: E402
    autocomplete_card_name,
    get_card,
    get_card_printings,
    get_card_rulings,
    random_card,
    search_cards,
)
from .combos import find_combos, search_combos  # noqa: E402
from .deck import (  # noqa: E402
    analyze_deck,
    analyze_mana_base,
    check_pod,
    compare_decks,
    deckbuilding_principles,
    deckbuilding_template,
    find_tokens,
    price_decklist,
    search_lands,
    simulate_deck,
)
from .edhrec_tools import edhrec_card, edhrec_recommendations  # noqa: E402
from .archidekt_tools import archidekt_get_deck, archidekt_popular_cards, archidekt_search_decks  # noqa: E402
from .reference import (  # noqa: E402
    moxfield_import_user,
    reference_card,
    reference_cards,
    reference_compare,
    reference_deck,
    reference_library,
    reference_principles,
)
from .skills_tool import get_skill  # noqa: E402
