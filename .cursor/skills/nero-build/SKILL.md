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

If `reference_principles` is not in this session, say so and stop. Do not invent the report.

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
         search_combos                   overlapping lines, pieces good alone
         reference_cards                 his cards in these colours
         get_card on every add           oracle, identity, Commander legal
         analyze_deck + price_decklist + find_combos + simulate_deck
```

1. `reference_principles(source="nero")`. Grade the list against what the tool returns. Do not recite principles from memory.
2. `get_card` on the commander. Write the rule it breaks in one sentence. Vren is a removal deck that makes Rats. If you cannot name the bend, stop and say so.
3. `reference_deck` with the commander name. A hit means start from his `decklist` and his `notes.win_lines`. Say which deck. Then switch to the tune skill's scorecard on that list.
4. No hit: write 3–4 jobs a card must do for this commander. A card that does none is out. A card that does two is in.
5. `search_combos` for overlapping 2–4 card lines. Every piece must be good alone. Most lines should work without the commander. Do not make Thoracle / Breach the plan unless the user asked for that budget.
6. `reference_cards` with `color_identity` set, `min_decks=3`, `sort="decks"`. Pull interaction, ramp, draw, protection, stax, tutors. `max_mana_value=3` unless the bend needs a bigger card. These are candidates. Check each one against the jobs.
7. `get_card` (and `get_card_rulings` if the line depends on timing) before a card is in the list. `f:commander` and `id<=` the commander's colours on every `search_cards`.
8. Lands last. Count follows the plan (dork turbo vs landfall), not 38. Utility lands and MDFCs count as both a land and a spell.
9. `analyze_deck`, `price_decklist`, `find_combos`, then `simulate_deck` with the win lines. Default budget is about $100 for the deck. Re-price before telling anyone to buy.

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
