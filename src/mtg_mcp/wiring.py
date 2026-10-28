"""Shared HTTP clients and deck resolution for MCP tools."""

from __future__ import annotations

from typing import Any

from .archidekt import Archidekt
from .decklist import ParsedDeck, parse_decklist
from .edhrec import Edhrec
from .http import ApiError, HttpClient
from .scryfall import Scryfall
from .spellbook import Spellbook

_http: HttpClient | None = None


def set_http_client(http: HttpClient) -> None:
    """Swap the shared HTTP client (used by tests)."""
    global _http
    _http = http


def http_client() -> HttpClient:
    clients()
    assert _http is not None
    return _http


def clients() -> tuple[Scryfall, Spellbook, Edhrec]:
    global _http
    if _http is None:
        _http = HttpClient()
    return Scryfall(_http), Spellbook(_http), Edhrec(_http)


def archidekt() -> Archidekt:
    clients()
    assert _http is not None
    return Archidekt(_http)


def api_error(exc: ApiError) -> dict[str, Any]:
    return {"error": str(exc), "status": exc.status}


async def resolve_deck(
    decklist: str | ParsedDeck,
    commanders: list[str] | None = None,
) -> tuple[ParsedDeck, dict[str, dict[str, Any]], list[str]]:
    scryfall, _, _ = clients()
    deck = parse_decklist(decklist, commanders) if isinstance(decklist, str) else decklist
    cards, not_found = await scryfall.collection(e.name for e in deck.commanders + deck.main + deck.sideboard)
    return deck, cards, not_found
