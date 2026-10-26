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


from ..library import ROLES, decklist_text, deck_label, get_library, library_dir, reload_library
from ..moxfield import import_user


def _library_or_error():
    lib = get_library()
    if not lib.decks:
        return None, {"error": f"No reference library found in {library_dir()}. Import one with moxfield_import_user."}
    return lib, None



async def reference_library() -> dict[str, Any]:
    """Overview of the reference library: who the builders are and every deck with archetype and stats.

    The library holds real, tested decklists (first source: NeRo's ~$100 high-power Bracket 4 / budget cEDH lists)
    with the builder's own card tags, primer-derived notes and win lines. Start here, then use
    reference_principles, reference_cards, reference_deck, reference_card and reference_compare.
    """
    lib, err = _library_or_error()
    if err:
        return err
    decks = []
    for d in lib.decks:
        notes = d.get("notes", {})
        decks.append({
            "deck": deck_label(d), "id": d["id"], "source": d["source"], "name": d["name"],
            "commanders": d.get("commanders", []), "colors": d.get("colors"), "bracket": d.get("bracket"),
            "archetype": notes.get("archetype"), "views": d.get("views"), "updated": d.get("updated"),
            "has_primer_notes": bool(notes.get("plan")), "win_lines": len(notes.get("win_lines", [])),
            "placeholder": d.get("placeholder", False), "url": d.get("url"),
            **{k: v for k, v in lib.deck_stats(d).items() if k != "tagged_role_counts"},
        })
    return {
        "sources": [{k: s.get(k) for k in ("key", "author", "profile_url", "summary", "captured")} for s in lib.sources.values()],
        "decks": decks,
        "unique_cards": sum(1 for u in lib.usage.values() if u["decks"]),
        "roles": ROLES,
        "note": "price_usd_at_capture is for the exact printings in the list at capture time, excluding basics; "
                "cheapest printings are often lower. Re-check with price_decklist before buying.",
    }


async def reference_principles(source: str | None = None) -> dict[str, Any]:
    """The reference builders' deckbuilding principles distilled from their primers, with evidence decks and rules of thumb.

    Complements deckbuilding_principles (Budget Pub Stomper / Budget Bros). source: e.g. "nero" (default: all).
    """
    lib, err = _library_or_error()
    if err:
        return err
    out = []
    for key, s in lib.sources.items():
        if source and key != source:
            continue
        out.append({"source": key, "author": s.get("author"), "principles": s.get("principles", []),
                    "rules_of_thumb": s.get("rules_of_thumb", [])})
    return {"sources": out} if out else {"error": f"Unknown source {source!r}; have {sorted(lib.sources)}"}


async def reference_cards(
    role: str | None = None,
    color_identity: str | None = None,
    min_decks: int = 1,
    max_price: float | None = None,
    max_mana_value: float | None = None,
    query: str | None = None,
    theme: str | None = None,
    include_lands: bool = True,
    sort: Literal["decks", "price", "mana_value"] = "decks",
    limit: int = 50,
) -> dict[str, Any]:
    """Proven card choices from the reference library, ranked by how many of the builder's decks play them.

    - role: one of ramp, draw, tutor, counter, removal, wipe, protection, stax, combo, recursion, untap, clone,
      tokens, evasion, land (from the builder's own tags).
    - color_identity: e.g. "UB" returns only cards legal in a Dimir deck. Colourless cards always qualify.
    - min_decks: 3+ gives the builder's staples; 1 shows everything he has tried.
    - max_price: USD at capture time. theme: match his other tags (e.g. "-1/-1", "poison", "elf").
    Each card lists which decks run it, its roles, and decks still 'considering' it.
    """
    lib, err = _library_or_error()
    if err:
        return err
    if role and role.lower() not in ROLES:
        return {"error": f"Unknown role {role!r}. Use one of {ROLES}."}
    cards = lib.search_cards(role=role, color_identity=color_identity, min_decks=max(1, min_decks), max_price=max_price,
                             max_mana_value=max_mana_value, query=query, theme=theme, include_lands=include_lands,
                             sort=sort, limit=max(1, min(limit, 300)))
    return {"count": len(cards), "cards": cards}


async def reference_card(name: str) -> dict[str, Any]:
    """How the reference builders use one card: which decks run it, the roles they tag it with, and decks considering it."""
    lib, err = _library_or_error()
    if err:
        return err
    resolved = lib.resolve_card(name)
    if not resolved or resolved not in lib.usage:
        return {"name": name, "in_library": False, "note": "No reference deck plays or considers this card."}
    return {"in_library": True, **lib.card_entry(resolved)}


async def reference_deck(deck: str, include_cards: bool = True, include_considering: bool = False) -> dict[str, Any]:
    """One reference deck: plan, ideal turn, mulligan guide, win lines, key cards, stats and the full decklist.

    deck: commander name, deck name or Moxfield id (e.g. "Kefka", "Hapatra", "Vren").
    `decklist` goes straight into analyze_deck / find_combos; `notes.win_lines` into simulate_deck's win_lines.
    """
    lib, err = _library_or_error()
    if err:
        return err
    hits = lib.find_decks(deck)
    if not hits:
        return {"error": f"No reference deck matches {deck!r}.", "decks": [deck_label(d) for d in lib.decks]}
    d = hits[0]
    out: dict[str, Any] = {
        "deck": deck_label(d), "name": d["name"], "url": d.get("url"), "source": d["source"],
        "commanders": d.get("commanders"), "colors": d.get("colors"), "bracket": d.get("bracket"),
        "updated": d.get("updated"), "description": d.get("description"), "notes": d.get("notes", {}),
        "stats": lib.deck_stats(d),
    }
    if len(hits) > 1:
        out["other_matches"] = [deck_label(h) for h in hits[1:]]
    if include_cards:
        out["decklist"] = decklist_text(d, include_considering=include_considering)
        out["cards"] = [{"name": n, "qty": q, "board": b, "tags": t} for n, q, b, t in d["cards"]
                        if include_considering or b != "considering"]
    return out


async def reference_compare(
    decklist: str,
    commanders: list[str] | None = None,
    min_decks: int = 3,
    max_price: float | None = None,
    limit_per_role: int = 15,
) -> dict[str, Any]:
    """Compare a deck with the reference library: proven staples in its colour identity that it doesn't play, by role.

    Use it to tweak an existing deck. Raise min_decks for only the most-played staples, and set max_price for budget.
    Treat results as candidates to check against the deck's plan, not automatic adds.
    """
    lib, err = _library_or_error()
    if err:
        return err
    try:
        deck, cards, not_found = await _resolve_deck(decklist, commanders)
    except ApiError as exc:
        return _error(exc)
    if not deck.commanders:
        return {"error": "Couldn't tell the commander; pass commanders=[...]."}
    known = []
    for entry in deck.commanders:
        card = cards.get(entry.name.lower())
        if card is None:
            return {"error": f"Couldn't look up commander {entry.name!r}.", "unresolved_cards": not_found}
        known.append(card)
    colors = {c for card in known for c in (card.get("color_identity") or [])}
    identity = "".join(c for c in "WUBRG" if c in colors)
    names = [(cards.get(e.name.lower()) or {}).get("name", e.name) for e in deck.commanders + deck.main]
    result = lib.compare(names, identity, min_decks=max(1, min_decks), max_price=max_price, limit=limit_per_role)
    result["commanders"] = [e.name for e in deck.commanders]
    if not_found:
        result["unresolved_cards"] = not_found
    return result


async def moxfield_import_user(username: str, source_key: str | None = None, include_primers: bool = True,
                               max_decks: int = 100) -> dict[str, Any]:
    """Import (or refresh) every public Commander deck of a Moxfield user into the reference library.

    Saves decks with the author's card tags, card metadata, and raw primers (markdown) under
    <library>/<source_key>/. Existing hand-written notes for decks are kept. Moxfield has no official API,
    so this can break or be rate-limited (about 1 request per second, ~2 per deck).
    """
    try:
        result = await import_user(wiring.http_client(), username, library_dir(), source_key=source_key,
                                   include_primers=include_primers, max_decks=max(1, min(max_decks, 200)))
    except ApiError as exc:
        return {**_error(exc), "hint": "Moxfield may be blocking automated requests from this network."}
    reload_library()
    return result


def register(mcp) -> None:
    mcp.tool()(reference_library)
    mcp.tool()(reference_principles)
    mcp.tool()(reference_cards)
    mcp.tool()(reference_card)
    mcp.tool()(reference_deck)
    mcp.tool()(reference_compare)
    mcp.tool()(moxfield_import_user)
