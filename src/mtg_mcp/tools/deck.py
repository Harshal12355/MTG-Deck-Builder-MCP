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


from ..analysis import (
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
from ..scryfall import price_usd, summarize_card

from ..analysis import (
    LAND_CYCLES,
    analyze_mana,
    collect_deck_tokens,
    compare_decks_analysis,
    evaluate_pod,
)
from ..decklist import parse_decklist
from ..scryfall import price_usd, summarize_card


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


def register(mcp) -> None:
    mcp.tool()(analyze_deck)
    mcp.tool()(deckbuilding_template)
    mcp.tool()(deckbuilding_principles)
    mcp.tool()(simulate_deck)
    mcp.tool()(price_decklist)
    mcp.tool()(analyze_mana_base)
    mcp.tool()(search_lands)
    mcp.tool()(compare_decks)
    mcp.tool()(check_pod)
    mcp.tool()(find_tokens)
