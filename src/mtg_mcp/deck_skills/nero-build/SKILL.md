---
name: nero-build
description: >
  Build a new Commander deck the NeRo way with the mtg-deckbuilder MCP:
  commander bend first, overlapping cheap combos, density over tutors,
  ~$100 high-power Bracket 4. Use when the user asks to build, brew, or
  start a deck, names a commander with no list yet, or says NeRo, _NeRo,
  budget cEDH, or Bracket 4 on a budget.
---

# Build a deck the NeRo way

NeRo (@_NeRo) builds ~$100 high-power Bracket 4. The test is his primers, not the Command Zone template and not the EDHREC top list.

If `reference_principles` is not in this session, read `src/mtg_mcp/data/library/nero/source.json`, or `get_library()` with `PYTHONPATH=src` from the repo root. Same fallback for `reference_deck` and `reference_cards`. Say that you used the files. Do not recite principles from memory.

## Order

```
commander
    |
    v
reference_principles(source="nero")     the test
get_card(commander)                     the bend, in one sentence
reference_deck(commander)               his list, if he already built it
    |
    +-- yes --> start from that decklist. Do not rebuild it.
    |
    +-- no
         get_skill nero-read             bend, trap, jobs, win shape
         get_skill nero-lines            lines, or "no combo package"
         get_skill nero-hunt             veggies first, then double-duty cards
         analyze_deck + price_decklist + find_combos + simulate_deck
```

1. `reference_principles(source="nero")`. Grade the list against what the tool returns. Do not recite principles from memory.
2. `get_card` on the commander. Write the rule it breaks in one sentence. Vren is a removal deck that makes Rats. If you cannot name the bend, stop and say so.
3. `reference_deck` with the commander name. A hit means start from his `decklist` and his `notes.win_lines`. Say which deck. Then switch to the tune skill's scorecard on that list.
4. No hit: `get_skill("nero-read")`. Its jobs and win shape are the test for every later card. If you cannot name the bend, stop.
5. `get_skill("nero-lines")` before any synergy card. A one-spell or edict-pile win does not get a combo package.
6. `get_skill("nero-hunt")`. Draw, ramp, and interaction first. Then cards that do a job and the plan. `reference_cards` is inside that skill.
7. `get_card` (and `get_card_rulings` if the line depends on timing) before a card is in the list. `f:commander` and `id<=` the commander's colours on every `search_cards`.
8. Lands last, then the mana skill on the finished list. Count follows the plan (dork turbo vs landfall), not 38.
9. `analyze_deck`, `price_decklist`, `find_combos`, then the goldfish skill with the win lines. Default budget is about $100 for the deck. Re-price before telling anyone to buy. If `simulate_deck` is missing, write "not simulated".

`deckbuilding_template` is the wrong ruler here. Land count, interaction, and tutors come from `reference_principles` rules of thumb and from `analyze_deck`. `edhrec_recommendations` is a check for the cookie-cutter shell, not the shopping list. Call it with `budget="budget"` only after the list exists, and only to see what everyone else plays.

## Hand back

```
Bend:     <one sentence>
Jobs:     1 …  2 …  3 …  4 …
Started:  his <deck name>   |   new list
Price:    $__   (~$100)
Avg MV:   __    (thumb from the tool)
Lands:    __    (why this count)
Lines:    <2–4 overlapping lines; which pieces are dead alone>
Curve:    simulate — commander cast by the ideal turn, in %

List:     plain `1 Card Name` lines, commander first
```

Lead with the bend. Then the list. Then at most four cuts you almost made, each tied to a job or a number from the tools.

## Example

User: "Build me a $100 Hapatra."

`reference_deck("Hapatra")` hits. Hand back his plan (turn-2 Hapatra, -1/-1 tempo into a sacrifice loop), his win lines, and the scorecard from `analyze_deck` + `price_decklist` on that `decklist`. Do not brew a second Hapatra.
