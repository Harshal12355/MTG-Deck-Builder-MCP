"""MCP server exposing Magic: The Gathering deckbuilding tools.

Run:
    mtg-mcp                  # stdio (Claude Desktop, Claude Code, etc.)
    mtg-mcp --http           # streamable HTTP on 127.0.0.1:8000/mcp
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .analysis import (
    LAND_CYCLES,
    TEMPLATE_CATEGORIES,
    analyze,
    analyze_mana,
    card_roles,
    collect_deck_tokens,
    compare_decks_analysis,
    evaluate_pod,
    resolve_template,
    template_overlap,
)
from .archidekt import Archidekt, parse_deck_id
from .decklist import ParsedDeck, parse_decklist
from .edhrec import Edhrec
from .http import ApiError, HttpClient
from .goldfish import simulate
from .library import ROLES, decklist_text, deck_label, get_library, library_dir, reload_library
from .moxfield import import_user
from .principles import principles as build_principles
from .scryfall import Scryfall, price_usd, summarize_card
from .skills import fetch_skill, register_prompts, tool_description
from .spellbook import Spellbook

INSTRUCTIONS = """\
Tools for Magic: The Gathering questions and deckbuilding.

- Card facts, rules text and prices: search_cards / get_card. Never answer card text from memory; look it up.
- Rules questions about a card: get_card_rulings.
- A pasted decklist (Moxfield, Arena, Archidekt, MTGO or plain text): analyze_deck first (reports WotC Bracket 1-5,
  0-10 Power Score, 3-School Score, and 10-axis Enabler x Payoff synergy; pass include_combos=True to include
  Commander Spellbook combos in one call), then find_combos, analyze_mana_base, and edhrec_recommendations.
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
- To test how a deck plays, call simulate_deck with its win lines (groups of card names). Compare runs
  before and after changes rather than reading the numbers as win rates.
- Real decks people have built: archidekt_search_decks (by commander, card, name, owner, colours, bracket),
  archidekt_get_deck for one deck's full list (its `decklist` field can go straight into analyze_deck / find_combos),
  and archidekt_popular_cards to see what the most-viewed Archidekt decks for a commander actually run.
- Reference library (reference_* tools): real, tested budget high-power decks from builders we learn from
  (first source: NeRo, ~$100 Bracket 4 / budget cEDH lists with primers). Use it when building or tuning:
  reference_principles for the builder's principles, reference_cards for proven card choices by role / colour
  identity / price, reference_deck for a full list with its win lines (pass them to simulate_deck),
  reference_card to see how a card was used, and reference_compare to find proven staples a deck is missing.
  Library prices are capture-time snapshots; re-check with price_decklist. moxfield_import_user adds or refreshes a builder.
- Deckbuilding skills: call get_skill and follow what it returns.
  nero-build when there is a commander and no list. nero-tune when a decklist or a link is already here.
  All three schools run on the same list (NeRo + Defcat + Based 33-card). nero-read, then defcat-read, before naming cards.
  nero-lines for the win (one spell, a pile, or overlapping combos).
  based-core locks the 33-card 1-game blueprint (1/3 of 99) and goldfishes that 33-card core first at low variance.
  nero-hunt for draw, ramp, interaction, then cards that also do the plan.
  defcat-turn rescores those cards for when in the turn they want to resolve.
  defcat-fuel only when defcat-read finds a mana-value bar (Rashmi, cascade, the first spell each turn).
  based-scale replicates the tested 33-card core two more times (33 x 3 = 99) with functional twins and zero 1/0/0 orphans.
  based-split deals an existing 99-card deck into 3 x 33 piles to expose uneven splits, 1/0/0 orphans, and slow value engines.
  nero-mana for a mana-base pass. nero-goldfish calls simulate_deck (on the 33-card core and the full 99). Do not stop a build or a tune before it, or before analyze_deck, price_decklist, and find_combos.
  moxfield-primer after the list is final: Moxfield `#tags` on every card plus a markdown primer to paste.
  The same text is available as MCP prompts under those names.
Prices are Scryfall's daily USD market prices. EDHREC and Archidekt data are best-effort.
"""

mcp = FastMCP("mtg-deckbuilder", instructions=INSTRUCTIONS)


@mcp.tool(description=tool_description())
def get_skill(name: str) -> dict[str, Any]:
    """Load one deckbuilding skill and follow the instructions it returns."""
    return fetch_skill(name)


register_prompts(mcp)

_http: HttpClient | None = None


def _clients() -> tuple[Scryfall, Spellbook, Edhrec]:
    global _http
    if _http is None:
        _http = HttpClient()
    return Scryfall(_http), Spellbook(_http), Edhrec(_http)


def _archidekt() -> Archidekt:
    _clients()  # make sure the shared client exists
    assert _http is not None
    return Archidekt(_http)


def set_http_client(http: HttpClient) -> None:
    """Swap the shared HTTP client (used by tests)."""
    global _http
    _http = http


def _error(exc: ApiError) -> dict[str, Any]:
    return {"error": str(exc), "status": exc.status}


async def _resolve_deck(decklist: str, commanders: list[str] | None) -> tuple[ParsedDeck, dict[str, dict[str, Any]], list[str]]:
    scryfall, _, _ = _clients()
    deck = parse_decklist(decklist, commanders)
    cards, not_found = await scryfall.collection(e.name for e in deck.commanders + deck.main + deck.sideboard)
    return deck, cards, not_found


# --------------------------------------------------------------------------- cards


@mcp.tool()
async def search_cards(
    query: str,
    order: Literal["edhrec", "name", "cmc", "usd", "released", "rarity", "power", "toughness"] = "edhrec",
    direction: Literal["auto", "asc", "desc"] = "auto",
    limit: int = 20,
    detail: Literal["brief", "full"] = "brief",
) -> dict[str, Any]:
    """Search cards with full Scryfall syntax (https://scryfall.com/docs/syntax).

    Examples: `t:legendary t:creature id:bg`, `o:"draw a card" id<=u cmc<=2 f:commander`,
    `otag:ramp id<=g usd<1`, `is:commander keyword:partner`.
    order="edhrec" sorts by popularity in Commander. detail="full" includes oracle text.
    """
    scryfall, _, _ = _clients()
    try:
        result = await scryfall.search(query, order=order, direction=direction, limit=max(1, min(limit, 100)))
    except ApiError as exc:
        return _error(exc)
    return {
        "query": query,
        "total_matches": result["total_cards"],
        "returned": len(result["cards"]),
        "cards": [summarize_card(c, detail) for c in result["cards"]],
        "warnings": result.get("warnings"),
    }


@mcp.tool()
async def get_card(name: str, set_code: str | None = None, exact: bool = False) -> dict[str, Any]:
    """Look up one card by name (fuzzy by default, so misspellings and partial names work).

    Returns oracle text, types, colours, legalities, price and the card's heuristic deck roles.
    """
    scryfall, _, _ = _clients()
    try:
        card = await scryfall.named(name, fuzzy=not exact, set_code=set_code)
    except ApiError as exc:
        return _error(exc)
    out = summarize_card(card)
    out["roles"] = card_roles(card) or None
    return out


@mcp.tool()
async def get_card_rulings(name: str) -> dict[str, Any]:
    """Official rulings and Gatherer notes for a card, plus its oracle text for context."""
    scryfall, _, _ = _clients()
    try:
        card = await scryfall.named(name)
        rulings = await scryfall.rulings(card)
    except ApiError as exc:
        return _error(exc)
    return {
        "card": card.get("name"),
        "oracle_text": summarize_card(card).get("oracle_text"),
        "rulings": [{"date": r.get("published_at"), "source": r.get("source"), "text": r.get("comment")} for r in rulings],
    }


@mcp.tool()
async def get_card_printings(name: str, limit: int = 15) -> dict[str, Any]:
    """Every printing of a card, cheapest first, with set and USD prices. Useful for budget builds."""
    scryfall, _, _ = _clients()
    try:
        card = await scryfall.named(name)
        prints = await scryfall.printings(card, limit=max(1, min(limit, 100)))
    except ApiError as exc:
        return _error(exc)
    return {
        "card": card.get("name"),
        "printings": [
            {
                "set": p.get("set"),
                "set_name": p.get("set_name"),
                "collector_number": p.get("collector_number"),
                "released": p.get("released_at"),
                "usd": (p.get("prices") or {}).get("usd"),
                "usd_foil": (p.get("prices") or {}).get("usd_foil"),
                "scryfall_uri": p.get("scryfall_uri"),
            }
            for p in prints
        ],
    }


@mcp.tool()
async def autocomplete_card_name(partial: str) -> dict[str, Any]:
    """Suggest up to 20 real card names for a partial or misspelled name."""
    scryfall, _, _ = _clients()
    try:
        return {"suggestions": await scryfall.autocomplete(partial)}
    except ApiError as exc:
        return _error(exc)


@mcp.tool()
async def random_card(query: str | None = None) -> dict[str, Any]:
    """A random card, optionally restricted by a Scryfall query (e.g. `is:commander id:ur`)."""
    scryfall, _, _ = _clients()
    try:
        return summarize_card(await scryfall.random(query))
    except ApiError as exc:
        return _error(exc)


# --------------------------------------------------------------------------- decks


@mcp.tool()
async def analyze_deck(
    decklist: str,
    format: str = "commander",
    commanders: list[str] | None = None,
    budget_per_card: float | None = None,
    template: dict[str, int] | None = None,
    include_combos: bool = False,
) -> dict[str, Any]:
    """Analyse a pasted decklist (Moxfield, Arena, Archidekt, MTGO or plain `1 Card Name` lines).

    Reports legality for the format (size, copies, colour identity, bans), official WotC Bracket (1-5)
    with `bracket_path` cuts, 0-10 Power Score (with Speed, Consistency, Saltiness, Interaction, Synergy,
    Resilience), 3-School Scorecard (NeRo + Defcat + Based 3x33), 10-axis Enabler x Payoff synergy,
    mana curve, colour pips vs land sources, card roles (ramp, draw, removal, wipes, tutors...),
    how the deck compares to the deckbuilding template, Game Changers, and total price.
    Pass `include_combos=True` to concurrently query Commander Spellbook so early vs late 2-card combos
    are factored into Bracket and Power Score in one call.
    """
    try:
        resolve_template(template)
    except ValueError as exc:
        return {"error": str(exc)}
    deck_parsed = parse_decklist(decklist, commanders)
    if not deck_parsed.playing:
        return {"error": "Couldn't find any cards in that decklist.", "unparsed_lines": deck_parsed.unparsed_lines[:10]}
    try:
        _, cards, not_found = await _resolve_deck(decklist, commanders)
        if include_combos:
            _, spellbook, _ = _clients()
            for e in deck_parsed.commanders:
                full_name = (cards.get(e.name.lower()) or {}).get("name")
                if full_name and "//" in full_name:
                    e.name = full_name
            combo_res = await spellbook.find_my_combos(deck_parsed, include_steps=False)
            combos = (combo_res.get("in_deck") or {}).get("combos") or []
        else:
            combos = None
    except ApiError as exc:
        return _error(exc)
    result = analyze(deck_parsed, cards, fmt=format, budget_per_card=budget_per_card, template=template, combos=combos)
    result["cards_not_found"] = sorted(set(result["cards_not_found"]) | set(not_found)) or None
    if deck_parsed.unparsed_lines:
        result["unparsed_lines"] = deck_parsed.unparsed_lines[:20]
    return result


@mcp.tool()
async def deckbuilding_template(template: dict[str, int] | None = None, color_identity: str | None = None) -> dict[str, Any]:
    """The Commander deckbuilding template to follow when building or tuning a deck.

    Defaults (The Command Zone's template): 38 lands, 10 ramp, 12 card advantage, 12 targeted disruption,
    6 mass disruption, 30 plan cards. Pass `template` to change any of them, e.g. {"lands": 36, "plan": 34}.
    Pass `color_identity` (e.g. "wub") to get Scryfall queries for each category limited to those colours.
    """
    try:
        targets = resolve_template(template)
    except ValueError as exc:
        return {"error": str(exc)}
    colors = f" id<={color_identity.lower()}" if color_identity else ""
    categories = {}
    for key, spec in TEMPLATE_CATEGORIES.items():
        entry: dict[str, Any] = {"target": targets[key], "default": spec["target"], "description": spec["description"]}
        if spec["scryfall"]:
            entry["search_query"] = f"{spec['scryfall']} f:commander{colors}"
        categories[key] = entry
    return {
        "categories": categories,
        "customized": sorted(k for k in targets if targets[k] != TEMPLATE_CATEGORIES[k]["target"]) or None,
        **template_overlap(targets),
        "how_to_use": [
            "Choose the plan cards first: the ones that make this commander's strategy work (edhrec_recommendations helps).",
            "Fill ramp, card advantage, targeted disruption and mass disruption next, preferring cards that also fit the plan.",
            "Count a card in every category it fills. The overlap figure above is how many cards need to do double duty.",
            "Add lands last, and match colour sources to the deck's colour pips.",
            "Check the finished list with analyze_deck, passing the same template.",
            "The template is a starting point, not a rule: for focused or budget builds see deckbuilding_principles.",
        ],
    }


@mcp.tool()
async def deckbuilding_principles() -> dict[str, Any]:
    """Principles for building focused, powerful Commander decks on a budget (~$100).

    Engine commander, win line first, build backwards from the ideal turn, average mana value near 2.0,
    synergy over staples, 29-34 lands instead of a rigid template, interaction that protects the win.
    Also returns `build_process` (Budget Bros MTG) for a greedy high-power Bracket 4 list at ~$100:
    read the commander past the theme (what locks, which mana you still pay), pick the win before synergy,
    fill draw/ramp/interaction above a normal video list, then utility cards that also do the plan.
    Cut the 4-mana enabler that does nothing the turn you cast it. Five colors is allowed.
    Search with get_skill: nero-read, defcat-read, nero-lines, based-core, nero-hunt, defcat-turn, based-scale, based-split.
    defcat-fuel only when the commander sets a mana-value bar.
    Use with deckbuilding_template and analyze_deck when building or tuning a deck.
    """
    return build_principles()


@mcp.tool()
async def simulate_deck(
    decklist: str,
    commanders: list[str] | None = None,
    win_lines: list[list[str]] | None = None,
    turns: int = 8,
    trials: int = 5000,
    on_play: bool = True,
    extra_cards_per_turn: int = 0,
    seed: int | None = None,
    mulligan_targets: list[dict[str, Any]] | None = None,
    track_card_impact: bool = False,
) -> dict[str, Any]:
    """Goldfish a deck: shuffle and play it out thousands of times to see how fast it sets up.

    Reports how often 7-card hands are kept, the chance the commander can be cast by each turn
    (colored pips included, plus the same chance if color is ignored), median cards left in hand,
    the chance a non-ramp spell has been cast, and for each win line the chance it can be paid for
    (`assembled_by_turn`) versus merely drawn (`seen_by_turn`). Tutors in hand stand in for a missing piece.
    Pass `mulligan_targets` (e.g. `[{"category": "land", "count": 3, "by_turn": 3}, {"category": "ramp", "count": 1, "by_turn": 2}]`)
    to run EDHcheck's Mulligan Strategy Calculator (`ceil(count/2)` opener rule + London mulligan).
    Pass `track_card_impact=True` to run single-card knockout attribution (swaps each active card with a blank
    using the same RNG seed to measure how much it accelerates the commander and win lines).
    """
    if not 1 <= turns <= 15:
        return {"error": "turns must be from 1 to 15."}
    if not 100 <= trials <= 50000:
        return {"error": "trials must be from 100 to 50000."}
    if not 0 <= extra_cards_per_turn <= 5:
        return {"error": "extra_cards_per_turn must be from 0 to 5."}
    try:
        deck, cards, not_found = await _resolve_deck(decklist, commanders)
    except ApiError as exc:
        return _error(exc)
    if not deck.playing:
        return {"error": "Couldn't find any cards in that decklist.", "unparsed_lines": deck.unparsed_lines[:10]}
    result = simulate(
        deck, cards, win_lines=win_lines, turns=turns, trials=trials, on_play=on_play,
        extra_cards_per_turn=extra_cards_per_turn, seed=seed,
        mulligan_targets=mulligan_targets, track_card_impact=track_card_impact,
    )
    if "error" not in result:
        result["cards_not_found"] = sorted(set(result.get("cards_not_found") or []) | set(not_found)) or None
    return result


@mcp.tool()
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


@mcp.tool()
async def search_combos(query: str, limit: int = 10) -> dict[str, Any]:
    """Search Commander Spellbook combos, most popular first.

    Query syntax examples: `card:"Thassa's Oracle"`, `result:"infinite mana" id<=bg`, `cards=2 result:"win the game"`.
    """
    _, spellbook, _ = _clients()
    try:
        return await spellbook.search(query, limit=max(1, min(limit, 50)))
    except ApiError as exc:
        return _error(exc)


@mcp.tool()
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
    scryfall, _, edhrec = _clients()
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
        return _error(exc)


@mcp.tool()
async def edhrec_card(name: str) -> dict[str, Any]:
    """EDHREC data for a card: the commanders that play it most and cards commonly played with it."""
    scryfall, _, edhrec = _clients()
    try:
        card = await scryfall.named(name)
        return await edhrec.card(card.get("name", name))
    except ApiError as exc:
        return _error(exc)


@mcp.tool()
async def price_decklist(
    decklist: str,
    currency: Literal["usd", "eur"] = "usd",
    budget_target: float | None = None,
) -> dict[str, Any]:
    """Quick price check of a decklist: per-card USD (TCGplayer) or EUR (Cardmarket) price and total, most expensive first.

    Pass `budget_target` to see which priciest non-commander cards would need to be cut to get under that target.
    """
    scryfall, _, _ = _clients()
    deck = parse_decklist(decklist)
    entries = deck.playing + deck.sideboard
    cmd_names = {e.name.lower() for e in deck.commanders}
    try:
        cards, not_found = await scryfall.collection(e.name for e in entries)
    except ApiError as exc:
        return _error(exc)
    rows = []
    for e in entries:
        c = cards.get(e.name.lower())
        if c is None:
            continue
        p = price_usd(c, currency=currency)
        if currency == "eur" and p is None:
            p = price_usd(c, currency="usd")
        total_p = round(p * e.quantity, 2) if p is not None else None
        row: dict[str, Any] = {"card": c.get("name"), "qty": e.quantity, "usd_each": p, "usd_total": total_p}
        if currency == "eur":
            row["eur_each"] = p
            row["eur_total"] = total_p
        rows.append(row)
    rows.sort(key=lambda r: -(r["usd_total"] or 0))
    total = round(sum(r["usd_total"] or 0 for r in rows), 2)
    out: dict[str, Any] = {
        "currency": currency,
        "total_usd": total,
        "cards": rows,
        "no_price_listed": [r["card"] for r in rows if r["usd_each"] is None] or None,
        "cards_not_found": not_found or None,
    }
    if currency == "eur":
        out["total_eur"] = total
    if budget_target is not None and total > budget_target:
        running = total
        cuts = []
        for r in rows:
            if running <= budget_target:
                break
            if (r["card"] or "").lower() in cmd_names or not r["usd_total"]:
                continue
            running = round(running - r["usd_total"], 2)
            cuts.append({"card": r["card"], "saves": r["usd_total"]})
        out["budget_target"] = budget_target
        out["suggested_cuts_to_hit_budget"] = cuts
        out["total_after_cuts"] = running
    return out


@mcp.tool()
async def analyze_mana_base(
    decklist: str,
    commanders: list[str] | None = None,
) -> dict[str, Any]:
    """Analyse a Commander mana base the EDHcheck / Frank Karsten way.

    Computes a 0-100 Mana Base Grade (S down to D-), Karsten's 99-card recommended land count
    (`31.42 + 3.13 * avg_cmc - 0.75 * ramp * 0.28`), Tipping Point turn (80% and 90% on-curve mana),
    exact hypergeometric per-color source requirements (`90%` cast probability with `+2` turn grace for Instants),
    color deficits, turn 1-8 cast rates by color, and land cycle speed breakdown (untapped / conditional / tapped).
    """
    try:
        deck, cards, not_found = await _resolve_deck(decklist, commanders)
    except ApiError as exc:
        return _error(exc)
    if not deck.playing:
        return {"error": "Couldn't find any cards in that decklist."}
    out = analyze_mana(deck, cards)
    out["cards_not_found"] = not_found or None
    return out


@mcp.tool()
async def search_lands(
    color_identity: str | None = None,
    cycle: str | None = None,
    speed: Literal["untapped", "conditional", "tapped"] | None = None,
    max_price: float | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Browse and search Commander land cycles (EDHcheck Land Database) via live Scryfall.

    - cycle: e.g. `fetch`, `dual`, `shock`, `bond`, `pain`, `fast`, `slow`, `check`, `pathway`, `verge`,
      `filter`, `canopy`, `battle`, `reveal`, `surveil`, `tri`, `bounce`, `scry`, `bike`, `mdfc`, `any-color`,
      `panorama`, `gain`, `gate`. Omit `cycle` with no `color_identity` to list all 24 land cycles.
    - speed: filter cycles to `untapped`, `conditional`, or `tapped`.
    - color_identity: e.g. `"ubr"` restricts Scryfall results to lands legal in that commander identity (`id<=ubr`).
    - max_price: maximum USD price per land (e.g. `5.0`).
    """
    cycles = [
        c for c in LAND_CYCLES
        if (cycle is None or c["slug"] == cycle.lower().strip())
        and (speed is None or c["speed"] == speed)
    ]
    if not cycles:
        return {"error": f"Unknown land cycle {cycle!r}.", "available_cycles": [c["slug"] for c in LAND_CYCLES]}
    if cycle is None and color_identity is None and max_price is None:
        return {"cycles": cycles}

    scryfall, _, _ = _clients()
    picked = cycles[0]
    q_parts = [f"({picked['query']})", "f:commander"]
    if color_identity:
        q_parts.append(f"id<={color_identity.lower().strip()}")
    if max_price is not None:
        q_parts.append(f"usd<={max_price}")
    query = " ".join(q_parts)
    try:
        res = await scryfall.search(query, order="edhrec", limit=max(1, min(limit, 60)))
    except ApiError as exc:
        return _error(exc)
    return {
        "cycle": picked,
        "query": query,
        "total_matches": res["total_cards"],
        "lands": [summarize_card(c, "brief") for c in res["cards"]],
    }


@mcp.tool()
async def compare_decks(
    decklist_a: str,
    decklist_b: str,
    commanders_a: list[str] | None = None,
    commanders_b: list[str] | None = None,
) -> dict[str, Any]:
    """Compare two decklists side by side (EDHcheck Deck Compare).

    Resolves the union of both lists in a single Scryfall collection pass and reports `cards_added`,
    `cards_removed`, `similarity_pct`, and exact before/after deltas for WotC Bracket, 0-10 Power Score,
    Speed, Consistency, 3-School Score, average mana value, lands, ramp, card draw, interaction, tutors,
    Game Changers, and USD price.
    """
    scryfall, _, _ = _clients()
    deck_a = parse_decklist(decklist_a, commanders_a)
    deck_b = parse_decklist(decklist_b, commanders_b)
    if not deck_a.playing or not deck_b.playing:
        return {"error": "Both decklist_a and decklist_b must contain cards."}
    names = [e.name for e in deck_a.playing + deck_b.playing]
    try:
        cards, not_found = await scryfall.collection(names)
    except ApiError as exc:
        return _error(exc)
    out = compare_decks_analysis(deck_a, deck_b, cards)
    out["cards_not_found"] = not_found or None
    return out


@mcp.tool()
async def check_pod(
    decks: list[str],
    names: list[str] | None = None,
) -> dict[str, Any]:
    """Compare 2 to 4 Commander decks for table balance before turn one (EDHcheck Pod Checker).

    Resolves all decks in one shared Scryfall lookup, scores each deck's WotC Bracket, 0-10 Power Score,
    Speed, Consistency, and median goldfish commander turn, and returns a Pod Verdict
    (`balanced`, `slight`, `uneven`, or `mismatched`), outlier warnings, and per-seat Rule 0 disclosures.
    """
    if not 2 <= len(decks) <= 4:
        return {"error": "check_pod requires between 2 and 4 decklists."}
    scryfall, _, _ = _clients()
    parsed = [parse_decklist(d) for d in decks]
    if any(not p.playing for p in parsed):
        return {"error": "Every deck in `decks` must contain cards."}
    all_names = [e.name for p in parsed for e in p.playing]
    try:
        cards, not_found = await scryfall.collection(all_names)
    except ApiError as exc:
        return _error(exc)

    seats = []
    for idx, p in enumerate(parsed):
        rep = analyze(p, cards)
        sim = simulate(p, cards, turns=8, trials=400, seed=1)
        cmd_label = " + ".join(rep["commanders"]) if rep["commanders"] else f"Seat {idx + 1}"
        seat_name = names[idx] if names and idx < len(names) and names[idx] else cmd_label
        seats.append({
            "name": seat_name,
            "analysis": rep,
            "median_commander_turn": (sim.get("commander") or {}).get("median_turn"),
        })
    out = evaluate_pod(seats)
    out["cards_not_found"] = not_found or None
    return out


@mcp.tool()
async def find_tokens(
    decklist: str,
    commanders: list[str] | None = None,
) -> dict[str, Any]:
    """List every token a deck can create and suggest how many of each to bring (EDHcheck Token Finder).

    Accounts for batch token creation, repeatable triggers, board-scaling effects, and token doublers
    in the deck (e.g. Doubling Season, Parallel Lives, Mondrak).
    """
    try:
        deck, cards, not_found = await _resolve_deck(decklist, commanders)
    except ApiError as exc:
        return _error(exc)
    if not deck.playing:
        return {"error": "Couldn't find any cards in that decklist."}
    out = collect_deck_tokens(deck, cards)
    out["cards_not_found"] = not_found or None
    return out


# --------------------------------------------------------------------------- archidekt


@mcp.tool()
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
    scryfall, _, _ = _clients()
    try:
        if commander:
            commander = (await scryfall.named(commander)).get("name", commander)
        if card:
            card = (await scryfall.named(card)).get("name", card)
        return await _archidekt().search(
            name=name, commander=commander, card=card, fmt=format, owner=owner, colors=colors,
            exact_colors=exact_colors, bracket=bracket, order=order, page=page, limit=limit,
        )
    except ValueError as exc:
        return {"error": str(exc)}
    except ApiError as exc:
        return _error(exc)


@mcp.tool()
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
        return await _archidekt().deck_summary(deck_id, include_cards=include_cards)
    except ApiError as exc:
        return _error(exc)


@mcp.tool()
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
    scryfall, _, _ = _clients()
    try:
        resolved = (await scryfall.named(commander)).get("name", commander)
        exclude: set[str] = set()
        if decklist:
            exclude = {e.name for e in parse_decklist(decklist).playing}
        return await _archidekt().popular_cards(
            resolved, decks=max(1, min(decks, 30)), order=order, bracket=bracket,
            exclude=exclude, include_basics=include_basics, top=max(1, min(top, 200)),
        )
    except ApiError as exc:
        return _error(exc)


# --------------------------------------------------------------------------- reference library


def _library_or_error():
    lib = get_library()
    if not lib.decks:
        return None, {"error": f"No reference library found in {library_dir()}. Import one with moxfield_import_user."}
    return lib, None


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
async def reference_card(name: str) -> dict[str, Any]:
    """How the reference builders use one card: which decks run it, the roles they tag it with, and decks considering it."""
    lib, err = _library_or_error()
    if err:
        return err
    resolved = lib.resolve_card(name)
    if not resolved or resolved not in lib.usage:
        return {"name": name, "in_library": False, "note": "No reference deck plays or considers this card."}
    return {"in_library": True, **lib.card_entry(resolved)}


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
async def moxfield_import_user(username: str, source_key: str | None = None, include_primers: bool = True,
                               max_decks: int = 100) -> dict[str, Any]:
    """Import (or refresh) every public Commander deck of a Moxfield user into the reference library.

    Saves decks with the author's card tags, card metadata, and raw primers (markdown) under
    <library>/<source_key>/. Existing hand-written notes for decks are kept. Moxfield has no official API,
    so this can break or be rate-limited (about 1 request per second, ~2 per deck).
    """
    _clients()
    assert _http is not None
    try:
        result = await import_user(_http, username, library_dir(), source_key=source_key,
                                   include_primers=include_primers, max_decks=max(1, min(max_decks, 200)))
    except ApiError as exc:
        return {**_error(exc), "hint": "Moxfield may be blocking automated requests from this network."}
    reload_library()
    return result


# --------------------------------------------------------------------------- entry point


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
