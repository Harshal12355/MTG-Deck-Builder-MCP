#!/usr/bin/env python3
"""Move MCP tool handlers from server.py into tools/*.py (module-level functions)."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SERVER = REPO / "scripts" / "server_tool_source.py"
TOOLS = REPO / "src/mtg_mcp/tools"

COMMON = '''"""MCP tool implementations."""

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


'''

SECTIONS: list[tuple[str, str, int, int, list[str]]] = [
    (
        "cards.py",
        '''from ..analysis import card_roles
from ..forge import fetch_forge_tags
from ..scryfall import summarize_card

''',
        138,
        252,
        ["search_cards", "get_card", "get_card_rulings", "get_card_printings", "autocomplete_card_name", "random_card"],
    ),
    (
        "deck.py",
        '''from ..analysis import (
    LAND_CYCLES,
    TEMPLATE_CATEGORIES,
    analyze,
    analyze_mana,
    collect_deck_tokens,
    compare_decks_analysis,
    evaluate_pod,
    resolve_template,
    template_overlap,
)
from ..decklist import parse_decklist
from ..goldfish import simulate
from ..principles import principles as build_principles
from ..scryfall import price_usd

''',
        258,
        401,
        [
            "analyze_deck",
            "deckbuilding_template",
            "deckbuilding_principles",
            "simulate_deck",
        ],
    ),
    (
        "combos.py",
        '''from ..decklist import parse_decklist

''',
        402,
        429,
        ["find_combos", "search_combos"],
    ),
    (
        "edhrec_tools.py",
        '''from ..decklist import parse_decklist

''',
        431,
        483,
        ["edhrec_recommendations", "edhrec_card"],
    ),
]

DECK_EXTRA = (
    '''from ..analysis import (
    LAND_CYCLES,
    analyze_mana,
    collect_deck_tokens,
    compare_decks_analysis,
    evaluate_pod,
)
from ..decklist import parse_decklist
from ..scryfall import price_usd

''',
    485,
    701,
    [
        "price_decklist",
        "analyze_mana_base",
        "search_lands",
        "compare_decks",
        "check_pod",
        "find_tokens",
    ],
)

ARCHIDEKT = (
    "archidekt_tools.py",
    '''from ..archidekt import parse_deck_id

''',
    706,
    794,
    ["archidekt_search_decks", "archidekt_get_deck", "archidekt_popular_cards"],
)

REFERENCE = (
    "reference.py",
    '''from ..library import ROLES, decklist_text, deck_label, get_library, library_dir, reload_library
from ..moxfield import import_user


def _library_or_error():
    lib = get_library()
    if not lib.decks:
        return None, {"error": f"No reference library found in {library_dir()}. Import one with moxfield_import_user."}
    return lib, None


''',
    805,
    980,
    [
        "reference_library",
        "reference_principles",
        "reference_cards",
        "reference_card",
        "reference_deck",
        "reference_compare",
        "moxfield_import_user",
    ],
)


def extract(start: int, end: int) -> str:
    lines = SERVER.read_text(encoding="utf-8").splitlines(keepends=True)
    body = "".join(lines[start - 1 : end])
    return re.sub(r"^@mcp\.tool\(\)\n", "", body, flags=re.MULTILINE)


def register_block(names: list[str]) -> str:
    lines = [f"    mcp.tool()({name})" for name in names]
    return "def register(mcp) -> None:\n" + "\n".join(lines) + "\n"


def write_module(path: Path, extra: str, body: str, names: list[str]) -> None:
    path.write_text(COMMON + extra + "\n" + body + "\n" + register_block(names), encoding="utf-8")
    print("wrote", path)


def main() -> None:
    for filename, extra, start, end, names in SECTIONS:
        body = extract(start, end)
        if filename == "deck.py":
            body += extract(DECK_EXTRA[1], DECK_EXTRA[2])
            extra = SECTIONS[1][1] + DECK_EXTRA[0]
            names = names + DECK_EXTRA[3]
        write_module(TOOLS / filename, extra, body, names)

    write_module(TOOLS / ARCHIDEKT[0], ARCHIDEKT[1], extract(ARCHIDEKT[2], ARCHIDEKT[3]), ARCHIDEKT[4])
    write_module(TOOLS / REFERENCE[0], REFERENCE[1], extract(REFERENCE[2], REFERENCE[3]), REFERENCE[4])

    (TOOLS / "skills_tool.py").write_text(
        '''"""get_skill MCP tool."""

from __future__ import annotations

from typing import Any

from ..skills import fetch_skill, tool_description


def get_skill(name: str) -> dict[str, Any]:
    """Load one deckbuilding skill and follow the instructions it returns."""
    return fetch_skill(name)


def register(mcp) -> None:
    mcp.tool(description=tool_description())(get_skill)
''',
        encoding="utf-8",
    )

    (TOOLS / "__init__.py").write_text(
        '''"""Register all MCP tool groups."""

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
''',
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
