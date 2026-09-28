"""Parse pasted decklists.

Handles the common text exports:
  - Moxfield / MTGO / plain:   ``1 Sol Ring`` or ``1x Sol Ring``
  - Moxfield with printing:    ``1 Sol Ring (C21) 263 *F*``
  - MTG Arena:                 ``Commander`` / ``Deck`` / ``Sideboard`` headers
  - Archidekt:                 ``1x Sol Ring (c21) 263 [Ramp]`` / ``[Commander{top}]``
  - Deckstats / others:        ``1 Atraxa, Praetors' Voice *CMDR*``
  - Section markers:           ``// Commander``, ``Commander:``, ``SIDEBOARD:``
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SECTION_ALIASES = {
    "commander": "commander",
    "commanders": "commander",
    "command zone": "commander",
    "companion": "companion",
    "deck": "main",
    "main": "main",
    "mainboard": "main",
    "main deck": "main",
    "sideboard": "sideboard",
    "side": "sideboard",
    "maybeboard": "maybe",
    "maybe": "maybe",
    "considering": "maybe",
    "tokens": "ignore",
    "attractions": "ignore",
    "stickers": "ignore",
    "about": "ignore",
}

_LINE = re.compile(r"^\s*(?:(?P<qty>\d+)\s*x?\s+)?(?P<rest>.+?)\s*$", re.IGNORECASE)
# "(SET) 123" or "(SET) 123a" printing info, optionally followed by foil markers.
_PRINTING = re.compile(r"\s+\((?P<set>[A-Za-z0-9]{2,6})\)(?:\s+(?P<num>[\w★\-]+))?")
_FOIL = re.compile(r"\s+\*(?:F|E|FOIL|ETCHED)\*", re.IGNORECASE)
_CMDR = re.compile(r"\s*\*CMDR\*", re.IGNORECASE)
_BRACKETS = re.compile(r"\s*\[(?P<cats>[^\]]*)\]")
_TAGS = re.compile(r"\s+#\S.*$")  # Moxfield "#!Ramp #Draw" tags
_SECTION_LINE = re.compile(r"^\s*(?://\s*)?(?P<name>[A-Za-z ]+?)\s*(?:\(\d+\))?\s*:?\s*$")


@dataclass
class DeckEntry:
    name: str
    quantity: int = 1
    set_code: str | None = None
    collector_number: str | None = None
    categories: list[str] = field(default_factory=list)


@dataclass
class ParsedDeck:
    commanders: list[DeckEntry] = field(default_factory=list)
    main: list[DeckEntry] = field(default_factory=list)
    sideboard: list[DeckEntry] = field(default_factory=list)
    companion: list[DeckEntry] = field(default_factory=list)
    maybe: list[DeckEntry] = field(default_factory=list)
    unparsed_lines: list[str] = field(default_factory=list)

    @property
    def playing(self) -> list[DeckEntry]:
        """Cards that are actually in the deck (commanders + main)."""
        return self.commanders + self.main

    @property
    def card_count(self) -> int:
        return sum(e.quantity for e in self.playing)

    def all_names(self) -> list[str]:
        return [e.name for e in self.commanders + self.main + self.sideboard + self.companion]


def _section_for(line: str) -> str | None:
    m = _SECTION_LINE.match(line)
    if not m:
        return None
    return SECTION_ALIASES.get(m.group("name").strip().lower())


def parse_decklist(text: str, commanders: list[str] | None = None) -> ParsedDeck:
    deck = ParsedDeck()
    section = "main"
    saw_any_card = False
    blank_after_cards = False
    main_blocks: list[list[DeckEntry]] = [[]]

    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line:
            if saw_any_card:
                blank_after_cards = True
            continue

        sec = _section_for(line)
        if sec is not None:
            section = sec
            blank_after_cards = False
            continue
        if section == "ignore":
            continue  # e.g. Arena "About" block ("Name My Deck"), token lists
        if line.startswith("//") or line.startswith("#"):
            continue  # comments

        m = _LINE.match(line)
        if not m:
            deck.unparsed_lines.append(raw)
            continue
        qty = int(m.group("qty") or 1)
        rest = m.group("rest")

        is_cmdr = bool(_CMDR.search(rest))
        rest = _CMDR.sub("", rest)
        categories: list[str] = []
        for bm in _BRACKETS.finditer(rest):
            cats = re.sub(r"\{[^}]*\}", "", bm.group("cats"))
            categories += [c.strip() for c in cats.split(",") if c.strip()]
        rest = _BRACKETS.sub("", rest)
        rest = _TAGS.sub("", rest)
        rest = _FOIL.sub("", rest)
        set_code = number = None
        pm = _PRINTING.search(rest)
        if pm:
            set_code, number = pm.group("set").lower(), pm.group("num")
            rest = rest[: pm.start()]
        name = rest.strip().strip('"')
        if not name:
            deck.unparsed_lines.append(raw)
            continue

        entry = DeckEntry(name=name, quantity=qty, set_code=set_code, collector_number=number, categories=categories)
        lowered = {c.lower() for c in categories}
        target = section
        if is_cmdr or "commander" in lowered:
            target = "commander"
        elif lowered & {"sideboard"}:
            target = "sideboard"
        elif lowered & {"maybeboard", "maybe", "considering"}:
            target = "maybe"
        elif section == "main" and blank_after_cards:
            # Start a new blank-line-separated block in the default section.
            main_blocks.append([])
            blank_after_cards = False

        if target == "ignore":
            continue
        if target == "main":
            main_blocks[-1].append(entry)
        else:
            getattr(deck, {"commander": "commanders"}.get(target, target)).append(entry)
        blank_after_cards = False
        saw_any_card = True

    # Moxfield's plain export of a commander deck puts the commander(s) alone
    # after a blank line at the end. If the last block is 1-2 singletons and the
    # whole list is ~100 cards, those are the commanders; otherwise blank lines
    # were just grouping and everything is main deck.
    blocks = [b for b in main_blocks if b]
    if not deck.commanders and len(blocks) > 1 and len(blocks[-1]) <= 2 and all(e.quantity == 1 for e in blocks[-1]):
        total = sum(e.quantity for b in blocks for e in b)
        if 98 <= total <= 101:
            deck.commanders.extend(blocks.pop())
    for b in blocks:
        deck.main.extend(b)

    # Explicit commanders override / supplement what was parsed.
    if commanders:
        wanted = {c.strip().lower() for c in commanders if c.strip()}
        for bucket in (deck.main, deck.sideboard):
            for e in list(bucket):
                if e.name.lower() in wanted:
                    bucket.remove(e)
                    deck.commanders.append(e)
        have = {e.name.lower() for e in deck.commanders}
        for c in commanders:
            if c.strip() and c.strip().lower() not in have:
                deck.commanders.append(DeckEntry(name=c.strip()))

    return deck
