"""Goldfish simulation: shuffle a deck many times and measure how fast it sets up.

No opponents and no card-by-card rules engine. Each simulated game plays one
land a turn, casts mana sources as early as it can, and casts the commander
only when the colored pips can be paid. A win line counts when the mana can
cast every piece, not when the names have merely been drawn. The numbers compare
versions of a deck. They are not a win rate.
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass
from statistics import median
from typing import Any

from .analysis import card_roles
from .decklist import ParsedDeck
from .scryfall import front_type_line, oracle_text

ASSUMPTIONS = [
    "Goldfish: no opponents, no interaction, no combat.",
    "Commander lists draw on turn 1, including the starting player. on_play skips that draw only when the list has no commander.",
    "Each land or rock makes the colors on its card. One source pays one pip. Colorless mana pays generic costs only.",
    "A fetch with no mana symbols makes one mana of a basic color in the deck, or the commander's colors if the deck has no basic. That mana waits a turn when the fetched land enters tapped.",
    "One land per turn. Untapped lands are played before tapped ones. Extra land drops are not modeled.",
    "Mana creatures tap the turn after they are cast. Rocks and auras like Utopia Sprawl tap immediately.",
    "Rituals are spent only to pay the commander's cost. Leftover ritual mana is not kept.",
    "Land-fetching ramp adds one basic-colored mana next turn.",
    "assembled_by_turn: every piece has been drawn and the mana after ramp can cast the pieces still in hand. A tutor in hand finds one missing piece once its own cost is paid. seen_by_turn is the older count of names that have shown up.",
    "A piece written 'A | B' is satisfied by either card. Creature-only tutors find creature pieces only.",
    "Follow-up is the first spell that is not a land or a mana source. A spell that says 'draw N cards' draws them when cast. Triggered draws are not modeled.",
    "Mulligan: keep 2-5 lands with a cheap mana source, or 3-5 lands. The first mulligan is free. At most two.",
]

_WORD_N = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
_LAND_FETCH = re.compile(
    r"search your library for [^.]*\b(?:lands?|forests?|plains|islands?|swamps?|mountains?)\b[^.]*onto the battlefield"
    r"|put (?:a|an|up to \w+) (?:basic )?land cards? [^.]*onto the battlefield"
)
_FETCH_LAND = re.compile(r"search your library for [^.]*\bland")
_ENTERS_TAPPED = re.compile(r"enters(?: the battlefield)? tapped")
_TAP_ADD = re.compile(r"(?:\{(\d+)\},\s*)?\{t\}[^:]*: add ([^.\n]*)")
_DRAW = re.compile(r"\bdraw (a|an|one|two|three|four|five|\d+) cards?\b")
_ANY = frozenset("WUBRG")

Pool = tuple[int, list[frozenset[str]]]


@dataclass
class SimCard:
    name: str
    kind: str  # land | tapped_land | source | ritual | land_ramp | tutor | creature_tutor | other
    cmc: int = 0
    mana: int = 0  # mana a source adds per turn, or a ritual adds once
    sick: bool = False  # creature mana source: usable the turn after it is cast
    creature: bool = False
    generic: int = 0
    requirements: tuple[frozenset[str], ...] = ()
    sources: tuple[frozenset[str], ...] = ()  # each entry pays one pip of any color in the set
    colorless: int = 0
    draws: int = 0
    basic: bool = False
    flexible: bool = False  # fetch or land ramp: color filled in once the deck's basics are known
    interaction: bool = False
    # shortcut: {W/U} and {2/W} are one pip of those colors. Two-brid is not a generic-or-color choice.


def _clause_units(clause: str) -> tuple[int, list[frozenset[str]]]:
    best_c, best_s = 0, []
    for part in clause.split(" or "):
        colorless = 0
        sources: list[frozenset[str]] = []
        for sym in re.findall(r"\{([^}]+)\}", part):
            colors = frozenset(ch for ch in "WUBRG" if ch in sym.upper())
            if colors:
                sources.append(colors)
            elif sym.upper() == "C":
                colorless += 1
            elif sym.isdigit():
                colorless += int(sym)
        word = re.search(r"\b(one|two|three|four|five) mana\b", part)
        if word and colorless + len(sources) == 0:
            n = _WORD_N[word.group(1)]
            if "any color" in part or "any colour" in part:
                sources = [frozenset(_ANY)] * n
            else:
                colorless += n
        if colorless + len(sources) > best_c + len(best_s):
            best_c, best_s = colorless, sources
    return best_c, best_s


def _permanent_units(text: str, produced: list[str]) -> tuple[int, tuple[frozenset[str], ...]]:
    best = (0, ())
    for generic, clause in _TAP_ADD.findall(text):
        colorless, sources = _clause_units(clause)
        pay = int(generic or 0)
        while pay and colorless:
            colorless -= 1
            pay -= 1
        while pay and sources:
            sources.pop(0)
            pay -= 1
        if colorless + len(sources) > best[0] + len(best[1]):
            best = (colorless, tuple(sources))
    if best[0] + len(best[1]) == 0 and (
        "adds an additional" in text or re.search(r"\{t\}: untap target (?:forest|land)", text)
    ):
        colors = [c for c in produced if c in _ANY]
        return (0, (frozenset(colors or "G"),))
    return best


def _add_units(text: str) -> tuple[int, tuple[frozenset[str], ...]]:
    best = (0, ())
    for clause in re.findall(r"\badd ([^.\n]*)", text):
        colorless, sources = _clause_units(clause)
        if colorless + len(sources) > best[0] + len(best[1]):
            best = (colorless, tuple(sources))
    return best


def _cost_parts(card: dict[str, Any]) -> tuple[int, tuple[frozenset[str], ...]]:
    cost = card.get("mana_cost") or ""
    if not cost and card.get("card_faces"):
        cost = (card["card_faces"][0] or {}).get("mana_cost") or ""
    generic = 0
    reqs: list[frozenset[str]] = []
    for sym in re.findall(r"\{([^}]+)\}", cost):
        if sym.isdigit():
            generic += int(sym)
            continue
        if sym.upper().startswith("X"):
            continue
        colors = frozenset(ch for ch in "WUBRG" if ch in sym.upper())
        if colors:
            reqs.append(colors)
        else:
            generic += 1
    return generic, tuple(reqs)


def _draws(text: str) -> int:
    total = 0
    for sent in re.split(r"[.\n]", text):
        # A combat trigger or "unless they pay" is not a card this spell draws.
        if "opponent" in sent or "unless" in sent or "whenever" in sent:
            continue
        match = _DRAW.search(sent)
        if not match:
            continue
        word = match.group(1)
        total += int(word) if word.isdigit() else _WORD_N[word]
    return total


def _finish(sim: SimCard, card: dict[str, Any], text: str, roles: list[str] | None = None) -> SimCard:
    sim.generic, sim.requirements = _cost_parts(card)
    if sim.kind in ("other", "tutor", "creature_tutor"):
        sim.draws = _draws(text)
    if roles and any(r in ("removal", "counterspell", "board_wipe") for r in roles):
        sim.interaction = True
    return sim


def classify(name: str, card: dict[str, Any]) -> SimCard:
    tl = front_type_line(card)
    text = re.sub(r"\([^)]*\)", "", oracle_text(card).lower())
    front = text.split("\n//\n")[0]
    cmc = int(float(card.get("cmc") or 0))
    creature = "Creature" in tl
    produced = list(card.get("produced_mana") or [])
    if "Land" in tl:
        colors = [c for c in produced if c in _ANY]
        tapped = bool(_ENTERS_TAPPED.search(front))
        basic = "Basic" in tl
        if colors:
            kind = "tapped_land" if tapped else "land"
            return _finish(SimCard(name, kind, sources=(frozenset(colors),), basic=basic), card, front)
        if _FETCH_LAND.search(front):
            # The land you find enters tapped whenever the fetch says so, so the mana waits.
            kind = "tapped_land" if "tapped" in front else "land"
            return _finish(SimCard(name, kind, flexible=True, basic=basic), card, front)
        return _finish(SimCard(name, "tapped_land" if tapped else "land", colorless=1, basic=basic), card, front)
    roles = card_roles(card)
    is_permanent = not any(t in tl for t in ("Instant", "Sorcery"))
    if is_permanent:
        colorless, sources = _permanent_units(front, produced)
        if colorless + len(sources) > 0:
            return _finish(
                SimCard(name, "source", cmc, colorless + len(sources), sick=creature, creature=creature,
                        sources=sources, colorless=colorless),
                card, front, roles,
            )
    elif _LAND_FETCH.search(front):
        return _finish(SimCard(name, "land_ramp", cmc, 1, flexible=True), card, front, roles)
    else:
        colorless, sources = _add_units(front)
        amount = colorless + len(sources)
        if "ramp" in roles and amount > cmc:
            return _finish(
                SimCard(name, "ritual", cmc, amount, sources=sources, colorless=colorless),
                card, front, roles,
            )
    if "tutor" in roles:
        only_creatures = re.search(r"search your library for (?:a|an|up to \w+) [^.]*?creature cards?", front)
        return _finish(SimCard(name, "creature_tutor" if only_creatures else "tutor", cmc, creature=creature), card, front, roles)
    return _finish(SimCard(name, "other", cmc, creature=creature), card, front, roles)


def _keepable(hand: list[SimCard]) -> bool:
    lands = sum(c.kind in ("land", "tapped_land") for c in hand)
    cheap = any(c.kind in ("source", "ritual", "land_ramp") and c.cmc <= 2 for c in hand)
    return 2 <= lands <= 5 and (cheap or lands >= 3)


def _bottom(hand: list[SimCard], n: int) -> list[SimCard]:
    hand = list(hand)
    for _ in range(n):
        lands = [c for c in hand if c.kind in ("land", "tapped_land")]
        if len(lands) > 4:
            hand.remove(lands[-1])
        else:
            spells = sorted((c for c in hand if c not in lands), key=lambda c: -c.cmc)
            hand.remove(spells[0] if spells else hand[-1])
    return hand


def _spell_cost(card: SimCard) -> tuple[int, list[frozenset[str]]]:
    if card.requirements or card.generic:
        return card.generic, list(card.requirements)
    return card.cmc, []


def _mana_of(card: SimCard) -> tuple[int, list[frozenset[str]]]:
    if card.sources:
        return card.colorless, list(card.sources)
    if card.kind in ("land", "tapped_land"):
        return max(card.colorless, 1), []
    if card.kind in ("source", "ritual", "land_ramp"):
        return card.mana or card.colorless, []
    return 0, []


def pay(colorless: int, sources: list[frozenset[str]], generic: int,
         requirements: list[frozenset[str]] | tuple[frozenset[str], ...]) -> Pool | None:
    """Spend mana. Returns the leftover pool, or None when the cost cannot be paid."""
    pool = list(sources)
    reqs = sorted(requirements, key=lambda req: sum(bool(req & src) for src in pool))
    if colorless + len(pool) < generic + len(reqs):
        return None
    for req in reqs:
        choices = [i for i, src in enumerate(pool) if req & src]
        if not choices:
            return None
        pool.pop(min(choices, key=lambda i: len(pool[i])))
    left = generic
    while left and colorless:
        colorless -= 1
        left -= 1
    while left and pool:
        pool.pop()
        left -= 1
    if left:
        return None
    return colorless, pool


def _cast_with_rituals(colorless: int, sources: list[frozenset[str]], generic: int,
                       reqs: list[frozenset[str]] | tuple[frozenset[str], ...],
                       rituals: list[SimCard]) -> tuple[int, list[frozenset[str]], list[SimCard]] | None:
    pool_c, pool_s = colorless, list(sources)
    used: list[SimCard] = []
    for ritual in sorted(rituals, key=lambda c: (c.cmc, c.name)):
        if pay(pool_c, pool_s, generic, reqs) is not None:
            break
        cost_g, cost_r = _spell_cost(ritual)
        paid = pay(pool_c, pool_s, cost_g, cost_r)
        if paid is None:
            continue
        pool_c, pool_s = paid
        add_c, add_s = _mana_of(ritual)
        pool_c += add_c
        pool_s += add_s
        used.append(ritual)
    paid = pay(pool_c, pool_s, generic, reqs)
    if paid is None:
        return None
    return paid[0], paid[1], used


def _line_ready(line: list[tuple[list[str], bool]], seen: set[str], tutors: dict[str, int]) -> bool:
    """Every piece seen, or the missing pieces can be found by the tutors seen."""
    missing = [is_creature for names, is_creature in line if not any(n in seen for n in names)]
    noncreature = sum(not c for c in missing)
    return noncreature <= tutors["tutor"] and len(missing) <= tutors["tutor"] + tutors["creature_tutor"]


def _bundle_cost(line: list[tuple[list[str], bool]], hand: list[SimCard],
                 deployed: set[str]) -> tuple[int, list[frozenset[str]]] | None:
    """Mana to cast every piece still in hand. Tutors in hand stand in for missing pieces."""
    held = {c.name: c for c in hand}
    generic = 0
    reqs: list[frozenset[str]] = []
    missing: list[bool] = []
    for names, is_creature in line:
        if any(n in deployed for n in names):
            continue
        card = next((held[n] for n in names if n in held), None)
        if card is None:
            missing.append(is_creature)
            continue
        g, r = _spell_cost(card)
        generic += g
        reqs.extend(r)
    regular = sorted((c for c in hand if c.kind == "tutor"), key=lambda c: c.cmc)
    critters = sorted((c for c in hand if c.kind == "creature_tutor"), key=lambda c: c.cmc)
    if sum(not flag for flag in missing) > len(regular):
        return None
    if len(missing) > len(regular) + len(critters):
        return None
    for is_creature in missing:
        if not is_creature or not critters or (regular and regular[0].cmc <= critters[0].cmc):
            tutor = regular.pop(0)
        else:
            tutor = critters.pop(0)
        g, r = _spell_cost(tutor)
        generic += g
        reqs.extend(r)
    return generic, reqs


def _play_game(library: list[SimCard], rng: random.Random, commander_cmc: int | None, turns: int,
               on_play: bool, extra: int, lines: list[list[tuple[list[str], bool]]],
               commander_cost: tuple[int, tuple[frozenset[str], ...]] | None = None,
               draw_first: bool = False) -> dict[str, Any]:
    mulligans = 0
    while True:
        rng.shuffle(library)
        hand = library[:7]
        if _keepable(hand) or mulligans >= 2:
            break
        mulligans += 1
    to_bottom = max(0, mulligans - 1)  # first mulligan is free in multiplayer Commander
    hand = _bottom(hand, to_bottom)
    deck_pos = 7
    seen = [c.name for c in hand]
    tutors = {"tutor": 0, "creature_tutor": 0}
    for c in hand:
        if c.kind in tutors:
            tutors[c.kind] += 1

    pool_c = pending_c = 0
    pool_s: list[frozenset[str]] = []
    pending_s: list[frozenset[str]] = []
    commander_turn = ignore_turn = follow_up = None
    color_cost = commander_cost if commander_cost is not None else (
        (commander_cmc, ()) if commander_cmc is not None else None
    )
    line_turn: list[int | None] = [None] * len(lines)
    seen_turn: list[int | None] = [None] * len(lines)
    any_turn = None
    deployed: set[str] = set()
    hand_sizes: list[int] = []

    def draw_one() -> None:
        nonlocal deck_pos
        if deck_pos >= len(library):
            return
        card = library[deck_pos]
        deck_pos += 1
        hand.append(card)
        seen.append(card.name)
        if card.kind in tutors:
            tutors[card.kind] += 1

    for turn in range(1, turns + 1):
        draws = (0 if (on_play and turn == 1 and not draw_first) else 1) + (extra if turn >= 2 else 0)
        for _ in range(draws):
            draw_one()
        pool_c += pending_c
        pool_s += pending_s
        pending_c, pending_s = 0, []
        land = next((c for c in hand if c.kind == "land"), None) or next(
            (c for c in hand if c.kind == "tapped_land"), None)
        if land:
            hand.remove(land)
            add_c, add_s = _mana_of(land)
            if land.kind == "land":
                pool_c += add_c
                pool_s += add_s
            else:
                pending_c += add_c
                pending_s += add_s
        rituals = [c for c in hand if c.kind == "ritual"]
        if commander_cmc is not None and ignore_turn is None:
            if _cast_with_rituals(pool_c, pool_s, commander_cmc, (), rituals) is not None:
                ignore_turn = turn
        if color_cost is not None and commander_turn is None:
            got = _cast_with_rituals(pool_c, pool_s, color_cost[0], color_cost[1], rituals)
            if got is not None:
                commander_turn = turn
                leftover_c, leftover_s, used = got
                for ritual in used:
                    hand.remove(ritual)
                # A ritual's extra mana pays the commander and nothing else.
                pool_c, pool_s = (0, []) if used else (leftover_c, leftover_s)
        for c in sorted((c for c in hand if c.kind in ("source", "land_ramp")), key=lambda c: (c.cmc, c.name)):
            paid = pay(pool_c, pool_s, *_spell_cost(c))
            if paid is None:
                continue
            pool_c, pool_s = paid
            hand.remove(c)
            add_c, add_s = _mana_of(c)
            if c.kind == "land_ramp" or c.sick:
                pending_c += add_c
                pending_s += add_s
            else:
                pool_c += add_c
                pool_s += add_s
        snap_c, snap_s = pool_c, list(pool_s)
        seen_set = set(seen)
        for i, line in enumerate(lines):
            if seen_turn[i] is None and _line_ready(line, seen_set, tutors):
                seen_turn[i] = turn
            bundle = None if line_turn[i] is not None else _bundle_cost(line, hand, deployed)
            if bundle is not None and pay(snap_c, snap_s, bundle[0], bundle[1]) is not None:
                line_turn[i] = turn
        if any_turn is None and any(t is not None for t in line_turn):
            any_turn = turn
        for _ in range(6):
            played = False
            options = [c for c in hand if c.kind in ("source", "land_ramp", "other", "tutor", "creature_tutor")]
            for c in sorted(options, key=lambda c: (c.cmc, c.name)):
                if c.kind in ("other", "tutor", "creature_tutor") and c.cmc == 0 and c.draws == 0 and not c.requirements:
                    continue
                paid = pay(pool_c, pool_s, *_spell_cost(c))
                if paid is None:
                    continue
                pool_c, pool_s = paid
                hand.remove(c)
                deployed.add(c.name)
                add_c, add_s = _mana_of(c)
                if c.kind == "land_ramp" or (c.kind == "source" and c.sick):
                    pending_c += add_c
                    pending_s += add_s
                elif c.kind == "source":
                    pool_c += add_c
                    pool_s += add_s
                else:
                    if follow_up is None:
                        follow_up = turn
                    for _draw in range(c.draws):
                        draw_one()
                played = True
                break
            if not played:
                break
        hand_sizes.append(len(hand))
    return {
        "mulligans": mulligans,
        "commander_turn": commander_turn,
        "commander_turn_ignoring_color": ignore_turn,
        "line_turns": line_turn,
        "seen_turns": seen_turn,
        "any_turn": any_turn,
        "hand_by_turn": hand_sizes,
        "follow_up_turn": follow_up,
    }


def _by_turn(turn_list: list[int | None], turns: int, trials: int) -> dict[str, float]:
    return {str(t): round(sum(1 for x in turn_list if x is not None and x <= t) / trials, 3) for t in range(1, turns + 1)}


def _fit(src: frozenset[str], identity: frozenset[str]) -> frozenset[str]:
    if not identity:
        return src
    return src & identity or src


def _matches_mulligan_category(card: SimCard, category: str) -> bool:
    cat = category.lower().strip()
    if cat in ("land", "lands"):
        return card.kind in ("land", "tapped_land")
    if cat in ("ramp", "mana"):
        return card.kind in ("source", "ritual", "land_ramp")
    if cat in ("interaction", "removal", "counter", "disruption"):
        return card.interaction
    if cat in ("draw", "card_draw", "card_advantage"):
        return card.draws > 0
    if cat in ("tutor", "tutors"):
        return card.kind in ("tutor", "creature_tutor")
    return card.name.lower() == cat


def _simulate_mulligan_targets(
    library: list[SimCard],
    targets: list[dict[str, Any]],
    trials: int,
    seed: int | None,
    penalty_per_mulligan: float = 0.15,
) -> dict[str, Any]:
    """EDHcheck Mulligan Strategy Calculator: ceil(want / 2) keep bar, free 1st mull, London down to 4."""
    parsed = []
    for t in targets:
        cat = str(t.get("category") or t.get("role") or "land")
        want = max(1, int(t.get("count") or t.get("min") or 1))
        by_turn = max(1, int(t.get("by_turn") or t.get("turn") or 3))
        in_deck = sum(1 for c in library if _matches_mulligan_category(c, cat))
        keep_min = min(in_deck, max(1, math.ceil(want / 2))) if in_deck > 0 else 0
        parsed.append({"category": cat, "want": want, "by_turn": by_turn, "in_deck": in_deck, "keep_min": keep_min})

    rng = random.Random((seed or 3804) ^ 0x5A5A)
    deck = list(library)
    n_lib = len(deck)
    success_raw = 0
    success_penalized = 0
    total_mulls = 0
    total_hand = 0
    cat_hits = [0] * len(parsed)

    for _ in range(trials):
        hand_size = 7
        mulls = 0
        non_free = 0
        used_free = False
        while True:
            rng.shuffle(deck)
            opener = deck[:hand_size]
            if all(
                sum(1 for c in opener if _matches_mulligan_category(c, p["category"])) >= p["keep_min"]
                for p in parsed
            ) or hand_size <= 4 or mulls >= 6:
                break
            mulls += 1
            if not used_free:
                used_free = True
            else:
                hand_size = max(4, hand_size - 1)
                non_free += 1

        total_mulls += mulls
        total_hand += hand_size
        all_ok = True
        for idx, p in enumerate(parsed):
            seen_slice = deck[: min(n_lib, hand_size + p["by_turn"])]
            got = sum(1 for c in seen_slice if _matches_mulligan_category(c, p["category"]))
            if got >= min(p["want"], p["in_deck"]) and p["in_deck"] >= p["want"]:
                cat_hits[idx] += 1
            else:
                all_ok = False
        if all_ok:
            success_raw += 1
            if rng.random() >= penalty_per_mulligan * non_free:
                success_penalized += 1

    return {
        "success_rate": round(success_penalized / trials, 3),
        "success_rate_no_tempo_penalty": round(success_raw / trials, 3),
        "average_mulligans": round(total_mulls / trials, 2),
        "average_kept_hand_size": round(total_hand / trials, 2),
        "targets": [
            {
                "category": p["category"],
                "copies_in_deck": p["in_deck"],
                "want": p["want"],
                "by_turn": p["by_turn"],
                "opener_keep_min": p["keep_min"],
                "hit_rate": round(cat_hits[i] / trials, 3),
            }
            for i, p in enumerate(parsed)
        ],
    }


def _compute_card_impact(
    library: list[SimCard],
    commander_cmc: int | None,
    commander_cost: tuple[int, tuple[frozenset[str], ...]] | None,
    turns: int,
    on_play: bool,
    extra_cards_per_turn: int,
    lines: list[list[tuple[list[str], bool]]],
    draw_first: bool,
    seed: int | None,
    trials: int,
) -> list[dict[str, Any]]:
    """EDHcheck Turn Clock knockout attribution: replace each active card with a blank using the same shuffles."""
    impact_trials = min(trials, 600)
    base_seed = seed if seed is not None else 49420
    base_rng = random.Random(base_seed)
    base_res = [
        _play_game(list(library), base_rng, commander_cmc, turns, on_play, extra_cards_per_turn, lines, commander_cost, draw_first)
        for _ in range(impact_trials)
    ]
    ideal_turn = min(turns, max(1, (commander_cmc or 4) - 1))
    base_cmd_rate = sum(1 for r in base_res if r["commander_turn"] is not None and r["commander_turn"] <= ideal_turn) / impact_trials
    base_win_rate = sum(1 for r in base_res if r["any_turn"] is not None and r["any_turn"] <= turns) / impact_trials

    line_names = {n for line in lines for names, _ in line for n in names}
    candidates = sorted({
        c.name for c in library
        if c.kind in ("source", "ritual", "land_ramp", "tutor", "creature_tutor") or c.draws > 0 or c.name in line_names
    })
    blank = SimCard("__Blank__", "other", cmc=99, generic=99)
    impacts = []
    for name in candidates[:35]:
        mod_lib = [blank if c.name == name else c for c in library]
        rng = random.Random(base_seed)
        mod_res = [
            _play_game(list(mod_lib), rng, commander_cmc, turns, on_play, extra_cards_per_turn, lines, commander_cost, draw_first)
            for _ in range(impact_trials)
        ]
        mod_cmd = sum(1 for r in mod_res if r["commander_turn"] is not None and r["commander_turn"] <= ideal_turn) / impact_trials
        mod_win = sum(1 for r in mod_res if r["any_turn"] is not None and r["any_turn"] <= turns) / impact_trials
        cmd_delta = round(base_cmd_rate - mod_cmd, 3)
        win_delta = round(base_win_rate - mod_win, 3)
        if cmd_delta != 0 or win_delta != 0:
            impacts.append({
                "card": name,
                f"commander_by_t{ideal_turn}_gain": cmd_delta,
                f"win_line_by_t{turns}_gain": win_delta,
            })
    impacts.sort(key=lambda x: (-(x[f"win_line_by_t{turns}_gain"] + x[f"commander_by_t{ideal_turn}_gain"]), x["card"]))
    return impacts[:15]


def simulate(deck: ParsedDeck, cards: dict[str, dict[str, Any]], *, win_lines: list[list[str]] | None = None,
             turns: int = 8, trials: int = 5000, on_play: bool = True, extra_cards_per_turn: int = 0,
             seed: int | None = None, mulligan_targets: list[dict[str, Any]] | None = None,
             track_card_impact: bool = False) -> dict[str, Any]:
    library: list[SimCard] = []
    missing: list[str] = []
    name_of: dict[str, str] = {}
    for e in deck.main:
        c = cards.get(e.name.lower())
        if c is None:
            missing.append(e.name)
            sim = SimCard(e.name, "other")
        else:
            sim = classify(e.name, c)
        name_of[e.name.lower()] = e.name
        library.extend([sim] * e.quantity)
    if not library:
        return {"error": "No cards to simulate. Put the deck's cards in the main deck section."}

    identity: frozenset[str] = frozenset()
    commander = None
    commander_cmc = None
    commander_cost = None
    if deck.commanders:
        commander = [e.name for e in deck.commanders]
        options = []
        for e in deck.commanders:
            c = cards.get(e.name.lower())
            if not c:
                continue
            identity |= frozenset(c.get("color_identity") or [])
            g, reqs = _cost_parts(c)
            cmc = int(float(c.get("cmc") or 0))
            if g + len(reqs) == 0 and cmc:
                g = cmc
            options.append((cmc, g, reqs))
        if options:
            commander_cmc, g, reqs = min(options, key=lambda o: o[0])
            commander_cost = (g, reqs)

    basic_colors = frozenset(c for card in library if card.basic for src in card.sources for c in src)
    # shortcut: a fetch finds any basic color in the deck, not a specific land you still have left
    flex = basic_colors or identity or _ANY
    stamped: set[int] = set()
    for card in library:
        if id(card) in stamped:
            continue
        stamped.add(id(card))
        if card.flexible:
            card.sources = (flex,)
        elif card.sources:
            card.sources = tuple(_fit(src, identity) for src in card.sources)

    by_name = {c.name: c for c in library}
    lines: list[list[tuple[list[str], bool]]] = []
    labels: list[list[str]] = []
    unknown_line_cards = []
    for line in win_lines or []:
        pieces = []
        for piece in line:
            names = []
            for alt in piece.split("|"):
                key = alt.strip().lower()
                if key in name_of:
                    names.append(name_of[key])
                elif key:
                    unknown_line_cards.append(alt.strip())
            if names:
                pieces.append((names, any(by_name[n].creature for n in names)))
        if pieces:
            lines.append(pieces)
            labels.append([" | ".join(names) for names, _ in pieces])

    rng = random.Random(seed)
    results = [
        _play_game(list(library), rng, commander_cmc, turns, on_play, extra_cards_per_turn, lines,
                   commander_cost, bool(deck.commanders))
        for _ in range(trials)
    ]

    out: dict[str, Any] = {
        "trials": trials,
        "on_play": on_play,
        "extra_cards_per_turn": extra_cards_per_turn,
        "opening_hand": {
            "kept_seven": round(sum(r["mulligans"] == 0 for r in results) / trials, 3),
            "average_mulligans": round(sum(r["mulligans"] for r in results) / trials, 2),
        },
        "development": {
            "median_hand_by_turn": {
                str(t): round(median([r["hand_by_turn"][t - 1] for r in results]), 1)
                for t in range(1, turns + 1)
            },
            "follow_up_by_turn": _by_turn([r["follow_up_turn"] for r in results], turns, trials),
        },
        "classified": {
            "mana_sources": sorted({c.name for c in library if c.kind == "source"}),
            "rituals": sorted({c.name for c in library if c.kind == "ritual"}),
            "land_ramp": sorted({c.name for c in library if c.kind == "land_ramp"}),
            "tutors": sorted({c.name for c in library if c.kind == "tutor"}),
            "creature_tutors": sorted({c.name for c in library if c.kind == "creature_tutor"}),
            "tapped_lands": sorted({c.name for c in library if c.kind == "tapped_land"}),
        },
    }
    if commander_cmc is not None:
        cast = [r["commander_turn"] for r in results]
        hit = [t for t in cast if t is not None]
        ignored = [r["commander_turn_ignoring_color"] for r in results]
        ignored_hit = [t for t in ignored if t is not None]
        out["commander"] = {
            "names": commander,
            "mana_value": commander_cmc,
            "castable_by_turn": _by_turn(cast, turns, trials),
            "castable_ignoring_color_by_turn": _by_turn(ignored, turns, trials),
            "median_turn": median(hit) if hit else None,
            "median_turn_ignoring_color": median(ignored_hit) if ignored_hit else None,
        }
    if lines:
        out["win_lines"] = [
            {
                "cards": labels[i],
                "assembled_by_turn": _by_turn([r["line_turns"][i] for r in results], turns, trials),
                "seen_by_turn": _by_turn([r["seen_turns"][i] for r in results], turns, trials),
            }
            for i in range(len(lines))
        ]
        out["any_win_line_by_turn"] = _by_turn([r["any_turn"] for r in results], turns, trials)
    if unknown_line_cards:
        out["win_line_cards_not_in_deck"] = unknown_line_cards
    if mulligan_targets:
        out["mulligan_strategy"] = _simulate_mulligan_targets(library, mulligan_targets, trials, seed)
    if track_card_impact:
        out["card_impact"] = _compute_card_impact(
            library, commander_cmc, commander_cost, turns, on_play, extra_cards_per_turn,
            lines, bool(deck.commanders), seed, trials,
        )
    out["cards_not_found"] = missing or None
    out["assumptions"] = ASSUMPTIONS
    return out
