"""Mana base grade, Karsten math, and land cycle metadata."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from ..decklist import ParsedDeck
from ..scryfall import front_type_line, oracle_text
from ._card_utils import COLORS, _front_lower, _pips
from .roles import card_roles

LAND_CYCLES: list[dict[str, str]] = [
    {"slug": "fetch", "label": "Fetch Lands", "speed": "untapped", "query": "is:fetchland unique:cards", "description": "Sacrifice to search for a land with a listed basic type."},
    {"slug": "dual", "label": "Original Dual Lands", "speed": "untapped", "query": "is:dual unique:cards", "description": "ABUR two-basic-type untapped duals."},
    {"slug": "shock", "label": "Shock Lands", "speed": "conditional", "query": "is:shockland unique:cards", "description": "Enter untapped if you pay 2 life; two basic land types."},
    {"slug": "bond", "label": "Bond Lands (Battlebond)", "speed": "conditional", "query": "is:bondland unique:cards", "description": "Enter untapped if you have two or more opponents (always in 4-player Commander)."},
    {"slug": "pain", "label": "Pain Lands", "speed": "untapped", "query": "is:painland unique:cards", "description": "Always untapped; colorless free or 1 damage for colored mana."},
    {"slug": "fast", "label": "Fast Lands", "speed": "conditional", "query": "is:fastland unique:cards", "description": "Enter untapped while you control two or fewer other lands."},
    {"slug": "slow", "label": "Slow Lands", "speed": "conditional", "query": "is:slowland unique:cards", "description": "Enter untapped if you control two or more other lands."},
    {"slug": "check", "label": "Check Lands", "speed": "conditional", "query": "is:checkland unique:cards", "description": "Enter untapped if you control a land with one of the listed basic types."},
    {"slug": "pathway", "label": "Pathway Lands (MDFC)", "speed": "untapped", "query": "t:land is:mdfc name:pathway unique:cards", "description": "Modal double-faced untapped lands; pick one color when played."},
    {"slug": "verge", "label": "Verge Lands", "speed": "untapped", "query": 't:land name:verge o:"Activate only if you control" unique:cards', "description": "Always untapped for primary color; secondary color online with a matching basic type."},
    {"slug": "filter", "label": "Filter Lands", "speed": "untapped", "query": "is:filterland unique:cards", "description": "Always untapped; filter 1 colored mana into 2 colored mana."},
    {"slug": "canopy", "label": "Horizon Lands (Canopy)", "speed": "untapped", "query": "is:canopyland unique:cards", "description": "Always untapped; pay 1 life for colored mana or sacrifice to draw a card."},
    {"slug": "battle", "label": "Battle Lands (Tango)", "speed": "conditional", "query": "is:tangoland unique:cards", "description": "Enter untapped if you control two or more basic lands; fetchable."},
    {"slug": "reveal", "label": "Reveal Lands (Snarls)", "speed": "conditional", "query": 't:land o:"As this land enters, you may reveal" unique:cards', "description": "Enter untapped if you reveal a matching land/creature type from hand."},
    {"slug": "surveil", "label": "Surveil Lands", "speed": "tapped", "query": 't:land o:"When this land enters, surveil 1" o:"enters tapped" unique:cards', "description": "Enter tapped and surveil 1; carry two basic land types (fetchable)."},
    {"slug": "tri", "label": "Tri-Lands & Triomes", "speed": "tapped", "query": "(is:triland or is:triome) unique:cards", "description": "Three-color tapped lands; Triomes have basic types and cycling."},
    {"slug": "bounce", "label": "Bounce Lands (Karoo)", "speed": "tapped", "query": "is:bounceland unique:cards", "description": "Enter tapped, return a land to hand, and tap for two mana."},
    {"slug": "scry", "label": "Scry Lands (Temples)", "speed": "tapped", "query": "is:scryland unique:cards", "description": "Enter tapped and scry 1."},
    {"slug": "bike", "label": "Cycling Duals (Bicycle)", "speed": "tapped", "query": "is:bikeland unique:cards", "description": "Enter tapped with two basic types and cycling {2}."},
    {"slug": "mdfc", "label": "MDFC Spell-Lands", "speed": "varies", "query": "is:mdfc t:land -name:pathway unique:cards", "description": "Spell on front face, land on back face."},
    {"slug": "any-color", "label": "Any-Color Lands", "speed": "varies", "query": 't:land -t:basic o:"add one mana of any color" unique:cards', "description": "Command Tower, Exotic Orchard, City of Brass, Mana Confluence, etc."},
    {"slug": "panorama", "label": "Basic Fetches (Landscapes / Panoramas)", "speed": "tapped", "query": 't:land (o:"Search your library for a basic land card" o:tapped or o:/search your library for a basic (forest|plains|island|swamp|mountain)/) unique:cards', "description": "Budget fetches that put a basic land onto the battlefield tapped."},
    {"slug": "gain", "label": "Gain Lands", "speed": "tapped", "query": "is:gainland unique:cards", "description": "Enter tapped and gain 1 life."},
    {"slug": "gate", "label": "Gates", "speed": "tapped", "query": "t:land t:gate unique:cards", "description": "Enter tapped; support Gate payoffs like Gond Gate and Maze's End."},
]


def _hypergeom_at_least(pop: int, successes: int, draws: int, wanted: int) -> float:
    """Exact probability of drawing >= wanted successes in `draws` from `pop` (hypergeometric)."""
    if wanted <= 0:
        return 1.0
    if successes < wanted or draws < wanted or pop <= 0:
        return 0.0
    draws = min(draws, pop)
    total_ways = math.comb(pop, draws)
    if total_ways == 0:
        return 0.0
    hit_ways = sum(
        math.comb(successes, k) * math.comb(pop - successes, draws - k)
        for k in range(wanted, min(successes, draws) + 1)
        if draws - k <= pop - successes
    )
    return min(1.0, max(0.0, hit_ways / total_ways))


def classify_land(card: dict[str, Any]) -> dict[str, str]:
    """Classify a land into its EDHcheck cycle and tempo speed (untapped | conditional | tapped)."""
    tl = front_type_line(card).lower()
    text = re.sub(r"\([^)]*\)", "", oracle_text(card).lower())
    name = (card.get("name") or "").lower()
    produced = [c for c in (card.get("produced_mana") or []) if c in COLORS]

    if "basic" in tl:
        return {"slug": "basic", "label": "Basic Land", "speed": "untapped"}
    if "search your library" in text and "land" in text:
        if "tapped" in text and "unless" not in text:
            return {"slug": "panorama", "label": "Basic Fetch (Tapped)", "speed": "tapped"}
        return {"slug": "fetch", "label": "Fetch Land", "speed": "untapped"}
    if "gate" in tl:
        return {"slug": "gate", "label": "Gate", "speed": "tapped"}
    if "return a land you control" in text:
        return {"slug": "bounce", "label": "Bounce Land (Karoo)", "speed": "tapped"}
    if "you gain 1 life" in text and "tapped" in text:
        return {"slug": "gain", "label": "Gain Land", "speed": "tapped"}
    if "pay 2 life" in text:
        return {"slug": "shock", "label": "Shock Land", "speed": "conditional"}
    if "two or more opponents" in text:
        return {"slug": "bond", "label": "Bond Land (Battlebond)", "speed": "conditional"}
    if "two or more basic lands" in text:
        return {"slug": "battle", "label": "Battle Land (Tango)", "speed": "conditional"}
    if "unless you control two or more other lands" in text:
        return {"slug": "slow", "label": "Slow Land", "speed": "conditional"}
    if "two or fewer other lands" in text:
        return {"slug": "fast", "label": "Fast Land", "speed": "conditional"}
    if re.search(r"unless you control an? [\w']+ or an? [\w']+", text):
        return {"slug": "check", "label": "Check Land", "speed": "conditional"}
    if "as this land enters, you may reveal" in text:
        return {"slug": "reveal", "label": "Reveal Land (Snarl)", "speed": "conditional"}
    if "verge" in name and "activate only if you control" in text:
        return {"slug": "verge", "label": "Verge Land", "speed": "untapped"}
    if "//" in name and "pathway" in name:
        return {"slug": "pathway", "label": "Pathway Land (MDFC)", "speed": "untapped"}
    if "deals 1 damage to you" in text or "pay 1 life" in text and "sacrifice" not in text:
        return {"slug": "pain", "label": "Pain Land", "speed": "untapped"}
    if "add two mana in any combination" in text:
        return {"slug": "filter", "label": "Filter Land", "speed": "untapped"}
    if "surveil 1" in text and "tapped" in text:
        return {"slug": "surveil", "label": "Surveil Land", "speed": "tapped"}
    if "scry 1" in text and "tapped" in text:
        return {"slug": "scry", "label": "Scry Land (Temple)", "speed": "tapped"}
    if "cycling" in text and "tapped" in text:
        return {"slug": "bike", "label": "Cycling Dual", "speed": "tapped"}
    if "sacrifice" in text and "draw a card" in text:
        return {"slug": "canopy", "label": "Horizon Land (Canopy)", "speed": "untapped"}
    if len(produced) >= 3 and "tapped" in text:
        return {"slug": "tri", "label": "Tri-Land / Triome", "speed": "tapped"}
    if "enters tapped" in text or "enters the battlefield tapped" in text:
        if any(w in text for w in ("unless", "you may pay", "if you control")):
            return {"slug": "conditional-utility", "label": "Conditional Land", "speed": "conditional"}
        return {"slug": "utility-tapped", "label": "Tapped Utility Land", "speed": "tapped"}
    if sum(t in tl for t in ("plains", "island", "swamp", "mountain", "forest")) >= 2:
        return {"slug": "dual", "label": "Original Dual Land", "speed": "untapped"}
    return {"slug": "utility", "label": "Untapped Land", "speed": "untapped"}


def land_produced_colors(
    card: dict[str, Any],
    identity: set[str],
    land_slug: str | None = None,
    has_commander: bool = False,
) -> list[str]:
    """Colors a card can produce within the commander's color identity (fetches count for all identity colors)."""
    text_low = oracle_text(card).lower()
    if not identity and (has_commander or "commander's color identity" in text_low):
        return []
    raw = [col for col in (card.get("produced_mana") or []) if col in COLORS]
    if not raw and "any color" in text_low:
        raw = list(COLORS)
    produced = [col for col in raw if not identity or col in identity]
    if not produced:
        slug = land_slug if land_slug is not None else classify_land(card)["slug"]
        # shortcut: fetches/panoramas count for every color in identity, upgrade to parse basic land types when checking off-color fetches
        if slug in {"fetch", "panorama"}:
            return [col for col in COLORS if col in identity]
    return produced


_land_produced_colors = land_produced_colors


def analyze_mana(
    deck: ParsedDeck,
    cards: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """EDHcheck-style Mana Base Analysis: Karsten live hypergeometric solver, tipping point, and 0-100 grade."""
    entries = [(e, cards.get(e.name.lower())) for e in deck.playing]
    resolved = [(e, c) for e, c in entries if c is not None]
    cmd_set = {_front_lower(e.name) for e in deck.commanders}

    total_cards = sum(e.quantity for e, _ in resolved)
    library_size = max(1, total_cards - len(cmd_set))

    lands = 0
    ramp_count = 0
    nonland_cmcs: list[float] = []
    pip_counts: Counter[str] = Counter()
    color_sources: Counter[str] = Counter()
    land_color_sources: Counter[str] = Counter()
    speed_counts: Counter[str] = Counter()
    groups: dict[str, dict[str, Any]] = {}
    pip_demands: list[dict[str, Any]] = []
    has_commander = bool(deck.commanders)
    commander_cards = [cards.get(e.name.lower()) for e in deck.commanders]
    identity: set[str] = {
        col for c in commander_cards if c for col in (c.get("color_identity") or []) if col in COLORS
    }
    if not has_commander:
        for _, c in resolved:
            for col in c.get("color_identity") or []:
                if col in COLORS:
                    identity.add(col)

    for e, c in resolved:
        is_cmd = _front_lower(c.get("name", e.name)) in cmd_set
        tl = front_type_line(c)

        if "Land" in tl:
            lands += e.quantity
            info = classify_land(c)
            speed_counts[info["speed"]] += e.quantity
            g = groups.setdefault(info["slug"], {"slug": info["slug"], "label": info["label"], "speed": info["speed"], "count": 0, "cards": []})
            g["count"] += e.quantity
            g["cards"].append(c.get("name", e.name))
            for col in land_produced_colors(c, identity, info["slug"], has_commander=has_commander):
                color_sources[col] += e.quantity
                land_color_sources[col] += e.quantity
        else:
            cmc = float(c.get("cmc") or 0)
            if not is_cmd:
                nonland_cmcs.extend([cmc] * e.quantity)
            roles = card_roles(c)
            if "ramp" in roles and not is_cmd:
                ramp_count += e.quantity
                for col in land_produced_colors(c, identity, "", has_commander=has_commander):
                    color_sources[col] += e.quantity
            cost = c.get("mana_cost") or ((c.get("card_faces") or [{}])[0].get("mana_cost", ""))
            pips = _pips(cost)
            # EDHcheck rule: reactive Instants get +2 turns of grace on Karsten pip demand
            demand_turn = max(1, round(cmc)) + (2 if "Instant" in tl else 0)
            for col, p_count in pips.items():
                pip_counts[col] += p_count * e.quantity
                if not is_cmd:
                    pip_demands.append({"color": col, "pips": p_count, "turn": demand_turn, "card": c.get("name", e.name)})

    avg_cmc = sum(nonland_cmcs) / len(nonland_cmcs) if nonland_cmcs else 3.0
    # Frank Karsten 99-card regression: 31.42 + 3.13 * avg_cmc - 0.75 * ramp * 0.28
    rec_lands = max(30, min(45, round(31.42 + 3.13 * avg_cmc - 0.75 * ramp_count * 0.28)))

    # Tipping point turn: earliest turn where hypergeometric probability of >= round(avg_cmc) lands+ramp >= 0.80 (and 0.90)
    target_mana = max(2, round(avg_cmc))
    effective_mana_cards = lands + round(ramp_count * 0.75)
    tipping_80 = next(
        (t for t in range(1, 16) if _hypergeom_at_least(library_size, effective_mana_cards, min(library_size, 7 + t), target_mana) >= 0.80),
        None,
    )
    tipping_90 = next(
        (t for t in range(1, 16) if _hypergeom_at_least(library_size, effective_mana_cards, min(library_size, 7 + t), target_mana) >= 0.90),
        None,
    )

    # Solve Karsten colored-source requirements per color (90% threshold)
    toughest: dict[str, dict[str, Any]] = {}
    for d in pip_demands:
        draws = min(library_size, 7 + d["turn"])
        needed = next(
            (s for s in range(d["pips"], library_size + 1) if _hypergeom_at_least(library_size, s, draws, d["pips"]) >= 0.90),
            library_size,
        )
        cur = toughest.get(d["color"])
        if cur is None or needed > cur["sources_needed"]:
            toughest[d["color"]] = {
                "color": d["color"],
                "pips_needed": d["pips"],
                "demand_turn": d["turn"],
                "demand_card": d["card"],
                "sources_needed": needed,
            }

    color_reqs = []
    for col, req in toughest.items():
        have = color_sources[col]
        color_reqs.append({
            **req,
            "sources_have": have,
            "land_sources_have": land_color_sources[col],
            "deficit": max(0, req["sources_needed"] - have),
        })
    color_reqs.sort(key=lambda r: (-r["deficit"], -r["sources_needed"], r["color"]))

    # Cast rate by color across turns 1..8
    cast_rate_by_color = {
        col: {
            str(t): round(_hypergeom_at_least(library_size, color_sources[col], min(library_size, 7 + t), 1), 3)
            for t in range(1, 9)
        }
        for col in COLORS
        if col in identity or color_sources[col]
    }

    # Overall on-curve cast rate across all pip demands
    if pip_demands:
        overall_cast_rate = sum(
            _hypergeom_at_least(library_size, color_sources[d["color"]], min(library_size, 7 + d["turn"]), d["pips"])
            for d in pip_demands
        ) / len(pip_demands)
    else:
        overall_cast_rate = 1.0

    # Opener 2+ lands probability (accounting for Commander's free mulligan when hand has <2 or >5 lands)
    p_two_plus = _hypergeom_at_least(library_size, lands, min(library_size, 7), 2)
    p_six_plus = _hypergeom_at_least(library_size, lands, min(library_size, 7), 6)
    p_mull = (1.0 - p_two_plus) + p_six_plus
    two_plus_lands = min(1.0, (p_two_plus - p_six_plus) + p_mull * p_two_plus)
    untapped_share = (speed_counts["untapped"] + 0.85 * speed_counts["conditional"]) / max(1, lands) if lands else 1.0

    # EDHcheck 0-100 gradeManaBase
    score = 100
    factors: list[dict[str, Any]] = []
    tp_pen = 55 if tipping_80 is None else (0 if tipping_80 <= 2 else 6 if tipping_80 == 3 else 16 if tipping_80 == 4 else 28 if tipping_80 == 5 else 40 if tipping_80 == 6 else 50)
    if tp_pen > 0:
        score -= tp_pen
        factors.append({"label": "Never reaches 80% on-curve consistency" if tipping_80 is None else f"Tipping point turn {tipping_80}", "impact": -tp_pen})
    total_deficit = sum(r["deficit"] for r in color_reqs)
    def_pen = min(15, 3 * total_deficit)
    if def_pen > 0:
        score -= def_pen
        factors.append({"label": f"{total_deficit} missing colored source(s)", "impact": -def_pen})
    if two_plus_lands < 0.90:
        op_pen = min(12, round((0.90 - two_plus_lands) * 80))
        if op_pen > 0:
            score -= op_pen
            factors.append({"label": f"Only {round(two_plus_lands * 100)}% of 7-card hands have 2+ lands", "impact": -op_pen})
    if untapped_share < 0.85:
        ut_pen = min(10, round((0.85 - untapped_share) * 50))
        if ut_pen > 0:
            score -= ut_pen
            factors.append({"label": f"Lands enter tapped too often (effective untapped {round(untapped_share * 100)}%)", "impact": -ut_pen})
    if overall_cast_rate < 0.95:
        cr_pen = min(15, round((0.95 - overall_cast_rate) * 60))
        if cr_pen > 0:
            score -= cr_pen
            factors.append({"label": f"Overall on-curve color cast rate {round(overall_cast_rate * 100, 1)}%", "impact": -cr_pen})

    score = max(0, min(100, round(score)))
    letter = (
        "S" if score >= 93 else "A+" if score >= 88 else "A" if score >= 83 else "A-" if score >= 78 else
        "B+" if score >= 73 else "B" if score >= 67 else "B-" if score >= 61 else "C+" if score >= 55 else
        "C" if score >= 48 else "C-" if score >= 42 else "D+" if score >= 36 else "D" if score >= 30 else "D-"
    )

    return {
        "grade": {"letter": letter, "score": score, "factors": factors},
        "lands": lands,
        "recommended_land_count": rec_lands,
        "land_count_delta": lands - rec_lands,
        "ramp_count": ramp_count,
        "average_cmc_nonland": round(avg_cmc, 2),
        "tipping_point": {"turn_80_pct": tipping_80, "turn_90_pct": tipping_90, "target_mana": target_mana},
        "opener_two_plus_lands_pct": round(two_plus_lands * 100, 1),
        "overall_on_curve_cast_pct": round(overall_cast_rate * 100, 1),
        "speed_breakdown": {
            "untapped": speed_counts["untapped"],
            "conditional": speed_counts["conditional"],
            "tapped": speed_counts["tapped"],
            "effective_untapped_pct": round(untapped_share * 100, 1),
        },
        "color_requirements": color_reqs,
        "cast_rate_by_color": cast_rate_by_color,
        "land_groups": sorted(groups.values(), key=lambda g: (-g["count"], g["slug"])),
    }
