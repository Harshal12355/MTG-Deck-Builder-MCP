"""Heuristic deck roles from oracle text."""

from __future__ import annotations

import re
from typing import Any

from ..scryfall import front_type_line, oracle_text

_ROLE_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "ramp": [
        re.compile(r"\badd (?:\{[wubrgcsx0-9/]+\}|one mana|two mana|three mana|x mana|an amount of|mana of any|that much)"),
        re.compile(r"search your library for (?:a|an|up to \w+|two) (?:basic )?(?:land|forest|plains|island|swamp|mountain)[^.]*onto the battlefield"),
        re.compile(r"put (?:a|an|up to \w+) (?:basic )?land cards? [^.]*onto the battlefield"),
        re.compile(r"you may play (?:an )?additional lands?"),
        re.compile(r"create (?:a|an|\w+) treasure token"),
    ],
    "card_draw": [
        re.compile(r"\bdraws? (?:a|an|one|two|three|four|five|x|that many|cards equal|\d+) (?:additional )?cards?"),
        re.compile(r"\bdraw cards equal"),
        re.compile(r"exile the top [^.]* cards? of your library[^.]*\. (?:until [^.]*, )?you may (?:play|cast)"),
        re.compile(r"reveal the top [^.]* of your library[^.]*put (?:that card|it|one of them) into your hand"),
    ],
    "removal": [
        re.compile(r"\b(?:destroy|exile) (?:target|up to (?:one|two|three|x) target|another target)"),
        re.compile(r"deals? (?:\d+|x|that much) damage to (?:any target|target (?:creature|planeswalker|attacking|blocking))"),
        re.compile(r"return (?:target|up to one target) (?:nonland permanent|creature|artifact|enchantment|permanent)[^.]* to its owner's hand"),
        re.compile(r"target (?:player|opponent) sacrifices"),
        re.compile(r"each opponent sacrifices"),
        re.compile(r"\bfights? (?:target|another target|up to one target)"),
        re.compile(r"target creature gets -\d+/-\d+|target creature gets -x/-x"),
    ],
    "counterspell": [re.compile(r"\bcounter (?:target|up to one target|that spell|it)\b")],
    "board_wipe": [
        re.compile(r"\b(?:destroy|exile) all (?:other )?(?:creatures|nonland permanents|permanents|artifacts|enchantments|nontoken)"),
        re.compile(r"\b(?:destroy|exile) each (?:other )?(?:creature|nonland permanent)"),
        re.compile(r"all (?:other )?creatures get -"),
        re.compile(r"deals? (?:\d+|x) damage to each (?:other )?creature"),
        re.compile(r"return all (?:other )?(?:creatures|nonland permanents|permanents)[^.]* to their owners' hands"),
        re.compile(r"each player sacrifices (?:all|each)"),
    ],
    "tutor": [
        re.compile(r"search your library for (?:a|an|up to \w+|two|three|four|any number of) (?!basic )(?![^.]*\b(?:land|plains|island|swamp|mountain|forest)\b)[^.]*cards?"),
        re.compile(r"\btransmute\b"),
    ],
    "protection": [
        re.compile(r"(?:gains?|have|has) (?:[a-z ,]*)?(?:hexproof|indestructible|shroud|protection from)"),
        re.compile(r"phase out"),
    ],
    "recursion": [
        re.compile(r"return [^.]*from your graveyard to (?:your hand|the battlefield)"),
        re.compile(r"(?:cast|play) [^.]* from your graveyard"),
    ],
}

_ANY_NUMBER = re.compile(r"a deck can have any number of cards named")
_UP_TO_N = re.compile(r"a deck can have up to (\w+) cards named")
_PIP = re.compile(r"\{([^}]+)\}")


_DRAW_HERE = re.compile(
    r"\bdraws? (?:a|an|one|two|three|four|five|x|that many|cards equal|\d+) (?:additional )?cards?|\bdraw cards equal"
)
_IMPULSE = re.compile(r"exile the top [^.]* cards? of your library[^.]*\. (?:until [^.]*, )?you may (?:play|cast)")


def _draw_gates(text: str) -> list[str]:
    """How a draw actually happens. Combat and opponents are not the same as a cantrip.

    shortcut: upkeep draws and "whenever you cast" stay plain card_draw. Split those out when a list's draws are mostly that.
    """
    gates: list[str] = []

    def add(gate: str) -> None:
        if gate not in gates:
            gates.append(gate)

    if _IMPULSE.search(text) and not re.search(r"\bwhenever\b|\bat the beginning\b", text):
        add("draw_on_cast")
    for sent in re.split(r"[.\n]", text):
        if not _DRAW_HERE.search(sent):
            continue
        if "combat damage" in sent:
            add("draw_on_hit")
        elif re.search(r"\bopponent\b", sent) and re.search(r"\bcasts?\b", sent):
            add("draw_on_their_spell")
        elif re.search(r"\bwhenever\b|\bat the beginning\b", sent):
            continue
        else:
            add("draw_on_cast")
    return gates


def card_roles(card: dict[str, Any]) -> list[str]:
    if "Land" in front_type_line(card):
        return []
    text = oracle_text(card).lower()
    # Ignore reminder text in parentheses.
    text = re.sub(r"\([^)]*\)", "", text)
    roles = [role for role, pats in _ROLE_PATTERNS.items() if any(p.search(text) for p in pats)]
    # Mana rocks/dorks: "{T}: Add" on a nonland permanent.
    if "ramp" not in roles and re.search(r"\{t\}[^:]*: add\b", text):
        roles.insert(0, "ramp")
    if "card_draw" in roles:
        roles.extend(_draw_gates(text))
    return roles
