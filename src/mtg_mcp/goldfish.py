"""Goldfish simulation: shuffle a deck many times and measure how fast it sets up.

No opponents and no card-by-card rules engine. Each simulated game plays one
land a turn, casts mana sources as early as it can, casts the commander as soon
as there is enough mana, and checks whether the cards for each win line have
been seen (with tutors standing in for missing pieces). The numbers are for
comparing versions of a deck, not exact win rates; results say so.
"""

from __future__ import annotations

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
    "Mana is counted by amount, not colour.",
    "One land per turn; untapped lands are played before tapped ones.",
    "Mana creatures can be tapped the turn after they are cast; mana rocks and auras like Utopia Sprawl at once.",
    "Rituals (e.g. Dark Ritual) are only used to cast the commander early.",
    "Land-fetching ramp spells add one mana from the next turn.",
    "Each tutor seen can find one missing piece of a win line; creature-only tutors find creature pieces only.",
    "A win-line piece written 'A | B' is satisfied by either card.",
    "Draw engines are not modelled; use extra_cards_per_turn to approximate them.",
    "Mulligan: keep 2-5 lands with a cheap mana source, or 3-5 lands; otherwise mulligan (first one free), at most twice.",
]

_SYMBOL = re.compile(r"\{([wubrgc])\}")
_WORD_N = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
_LAND_FETCH = re.compile(r"search your library for [^.]*\b(?:lands?|forests?|plains|islands?|swamps?|mountains?)\b[^.]*onto the battlefield|put (?:a|an|up to \w+) (?:basic )?land cards? [^.]*onto the battlefield")
_ENTERS_TAPPED = re.compile(r"enters(?: the battlefield)? tapped")


@dataclass
class SimCard:
    name: str
    kind: str  # land | tapped_land | source | ritual | land_ramp | tutor | creature_tutor | other
    cmc: int = 0
    mana: int = 0  # mana a source adds per turn, or a ritual adds once
    sick: bool = False  # creature mana source: usable the turn after it is cast
    creature: bool = False


_TAP_ADD = re.compile(r"(?:\{(\d+)\},\s*)?\{t\}[^:]*: add ([^.\n]*)")


def _clause_amount(clause: str) -> int:
    best = 0
    for part in clause.split(" or "):
        n = len(_SYMBOL.findall(part))
        m = re.search(r"\b(one|two|three|four|five) mana\b", part)
        if m:
            n = max(n, _WORD_N[m.group(1)])
        best = max(best, n)
    return best


def _mana_amount(text: str) -> int:
    """Net mana a permanent adds per turn ({1}, {T}: Add {B}{G} nets 1)."""
    best = 0
    for generic, clause in _TAP_ADD.findall(text):
        best = max(best, _clause_amount(clause) - int(generic or 0))
    if "adds an additional" in text or re.search(r"\{t\}: untap target (?:forest|land)", text):
        best = max(best, 1)
    return best


def _ritual_amount(text: str) -> int:
    return max((_clause_amount(c) for c in re.findall(r"\badd ([^.\n]*)", text)), default=0)


def classify(name: str, card: dict[str, Any]) -> SimCard:
    tl = front_type_line(card)
    text = re.sub(r"\([^)]*\)", "", oracle_text(card).lower())
    front = text.split("\n//\n")[0]
    cmc = int(float(card.get("cmc") or 0))
    creature = "Creature" in tl
    if "Land" in tl:
        return SimCard(name, "tapped_land" if _ENTERS_TAPPED.search(front) else "land")
    roles = card_roles(card)
    is_permanent = not any(t in tl for t in ("Instant", "Sorcery"))
    if is_permanent:
        amount = _mana_amount(front)
        if amount > 0:
            return SimCard(name, "source", cmc, amount, sick=creature, creature=creature)
    elif _LAND_FETCH.search(front):
        return SimCard(name, "land_ramp", cmc, 1)
    elif "ramp" in roles and _ritual_amount(front) > cmc:
        return SimCard(name, "ritual", cmc, _ritual_amount(front))
    if "tutor" in roles:
        only_creatures = re.search(r"search your library for (?:a|an|up to \w+) [^.]*?creature cards?", front)
        return SimCard(name, "creature_tutor" if only_creatures else "tutor", cmc, creature=creature)
    return SimCard(name, "other", cmc, creature=creature)


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


def _line_ready(line: list[tuple[list[str], bool]], seen: set[str], tutors: dict[str, int]) -> bool:
    """Every piece seen, or the missing pieces can be found by the tutors seen.

    A piece is a list of interchangeable card names; creature-only tutors can find creature pieces only.
    """
    missing = [is_creature for names, is_creature in line if not any(n in seen for n in names)]
    noncreature = sum(not c for c in missing)
    return noncreature <= tutors["tutor"] and len(missing) <= tutors["tutor"] + tutors["creature_tutor"]


def _play_game(library: list[SimCard], rng: random.Random, commander_cmc: int | None, turns: int,
               on_play: bool, extra: int, lines: list[list[tuple[list[str], bool]]]) -> dict[str, Any]:
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

    lands = tapped_pending = permanent_mana = sick_mana = 0
    commander_turn = None
    line_turn: list[int | None] = [None] * len(lines)
    any_turn = None

    for turn in range(1, turns + 1):
        draws = (0 if (on_play and turn == 1) else 1) + (extra if turn >= 2 else 0)
        for _ in range(draws):
            if deck_pos < len(library):
                card = library[deck_pos]
                deck_pos += 1
                hand.append(card)
                seen.append(card.name)
                if card.kind in tutors:
                    tutors[card.kind] += 1
        # untap: last turn's tapped land and summoning-sick sources come online
        lands += tapped_pending
        tapped_pending = 0
        permanent_mana += sick_mana
        sick_mana = 0
        land = next((c for c in hand if c.kind == "land"), None) or next((c for c in hand if c.kind == "tapped_land"), None)
        if land:
            hand.remove(land)
            if land.kind == "land":
                lands += 1
            else:
                tapped_pending += 1
        available = lands + permanent_mana
        if commander_cmc is not None and commander_turn is None:
            rituals = [c for c in hand if c.kind == "ritual"]
            boost = sum(c.mana - c.cmc for c in rituals) if available >= 1 else 0
            if available >= commander_cmc:
                commander_turn = turn
                available -= commander_cmc
            elif available + boost >= commander_cmc:
                commander_turn = turn
                for c in rituals:
                    hand.remove(c)
                available = 0
        for c in sorted((c for c in hand if c.kind in ("source", "land_ramp")), key=lambda c: c.cmc):
            if c.cmc <= available:
                hand.remove(c)
                available -= c.cmc
                if c.kind == "land_ramp":
                    tapped_pending += c.mana
                elif c.sick:
                    sick_mana += c.mana
                else:
                    permanent_mana += c.mana
                    available += c.mana
        seen_set = set(seen)
        for i, line in enumerate(lines):
            if line_turn[i] is None and _line_ready(line, seen_set, tutors):
                line_turn[i] = turn
        if any_turn is None and any(t is not None for t in line_turn):
            any_turn = turn
    return {"mulligans": mulligans, "commander_turn": commander_turn, "line_turns": line_turn, "any_turn": any_turn}


def _by_turn(turn_list: list[int | None], turns: int, trials: int) -> dict[str, float]:
    return {str(t): round(sum(1 for x in turn_list if x is not None and x <= t) / trials, 3) for t in range(1, turns + 1)}


def simulate(deck: ParsedDeck, cards: dict[str, dict[str, Any]], *, win_lines: list[list[str]] | None = None,
             turns: int = 8, trials: int = 5000, on_play: bool = True, extra_cards_per_turn: int = 0,
             seed: int | None = None) -> dict[str, Any]:
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

    commander = None
    commander_cmc = None
    if deck.commanders:
        cc = [cards.get(e.name.lower()) for e in deck.commanders]
        commander = [e.name for e in deck.commanders]
        # partners are cast separately; time to the first (cheapest) one is reported
        known = [int(float(c.get("cmc") or 0)) for c in cc if c]
        commander_cmc = min(known) if known else None

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
    results = [_play_game(list(library), rng, commander_cmc, turns, on_play, extra_cards_per_turn, lines)
               for _ in range(trials)]

    out: dict[str, Any] = {
        "trials": trials,
        "on_play": on_play,
        "extra_cards_per_turn": extra_cards_per_turn,
        "opening_hand": {
            "kept_seven": round(sum(r["mulligans"] == 0 for r in results) / trials, 3),
            "average_mulligans": round(sum(r["mulligans"] for r in results) / trials, 2),
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
        out["commander"] = {
            "names": commander,
            "mana_value": commander_cmc,
            "castable_by_turn": _by_turn(cast, turns, trials),
            "median_turn": median(hit) if hit else None,
        }
    if lines:
        out["win_lines"] = [
            {"cards": labels[i], "assembled_by_turn": _by_turn([r["line_turns"][i] for r in results], turns, trials)}
            for i in range(len(lines))
        ]
        out["any_win_line_by_turn"] = _by_turn([r["any_turn"] for r in results], turns, trials)
    if unknown_line_cards:
        out["win_line_cards_not_in_deck"] = unknown_line_cards
    out["cards_not_found"] = missing or None
    out["assumptions"] = ASSUMPTIONS
    return out
