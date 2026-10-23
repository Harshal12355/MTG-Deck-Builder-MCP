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
         get_skill defcat-read           when in the turn; bar, or "none"
         get_skill nero-lines            lines, or "no combo package"
         get_skill nero-hunt             veggies first, then double-duty cards
         get_skill defcat-turn           rescore those keeps
         get_skill defcat-fuel           only when the bar is real
         get_skill nero-mana
         analyze_deck + price_decklist + find_combos
         get_skill nero-goldfish        calls simulate_deck
         edhrec_recommendations + archidekt_popular_cards
```

1. `reference_principles(source="nero")`. Grade the list against what the tool returns. Do not recite principles from memory.
2. `get_card` on the commander. Write the rule it breaks in one sentence. Vren is a removal deck that makes Rats. If you cannot name the bend, stop and say so.
3. `reference_deck` with the commander name. A hit means start from his `decklist` and his `notes.win_lines`. Say which deck. Then switch to the tune skill's scorecard on that list.
4. No hit: `get_skill("nero-read")`, then `get_skill("defcat-read")`. NeRo jobs and the win shape are the test for every later card. Defcat adds the turn that card wants, and a mana-value bar when the commander compares one. `Bar: none` is a complete answer. If you cannot name the bend, stop.
5. `get_skill("nero-lines")` before any synergy card. A one-spell or edict-pile win does not get a combo package.
6. `get_skill("nero-hunt")`, then `get_skill("defcat-turn")` on those keeps. A keep that is blank on the turn the deck acts is a cut. Draw, ramp, and interaction first. Then cards that do a job and the plan. `reference_cards` is inside the hunt skill.
6b. `get_skill("defcat-fuel")` only when the bar is real. A fuel card still does a NeRo job the turn you cast it. `Bar: none` means no fuel package.
7. `get_card` (and `get_card_rulings` if the line depends on timing) before a card is in the list. `f:commander` and `id<=` the commander's colours on every `search_cards`.
8. Lands last, then `get_skill("nero-mana")` on the finished list. Count follows the plan (dork turbo vs landfall), not 38.
9. `analyze_deck`, `price_decklist`, `find_combos`, then `get_skill("nero-goldfish")`. That skill calls `simulate_deck`. Copy its hand-back into Curve. Do not invent a percent. If `simulate_deck` is missing, write "not simulated".
10. `edhrec_recommendations` with `budget="budget"` and the decklist, and `archidekt_popular_cards`. Both show the shell. Neither is the shopping list. `get_card_printings` before naming a printing to buy. `price_decklist` again before telling anyone to buy. Default budget is about $100 for the deck.

`deckbuilding_template` is the wrong ruler here. Land count, interaction, and tutors come from `reference_principles` rules of thumb and from `analyze_deck`. `edhrec_recommendations` is a check for the cookie-cutter shell, not the shopping list. Call it with `budget="budget"` only after the list exists, and only to see what everyone else plays.

## Hand back

```
Bend:     <one sentence>
When:     first main | second main | their turn
Bar:      none | what a cast spell sets
Jobs:     1 …  2 …  3 …  4 …
Fuel:     none | printed MV, mana you pay
Started:  his <deck name>   |   new list
Price:    $__   (~$100)
Avg MV:   __    (thumb from the tool)
Lands:    __    (why this count)
Lines:    <2–4 overlapping lines; which pieces are dead alone>
Curve:    nero-goldfish block (kept 7, cast by ideal turn, each line)

List:     plain `1 Card Name` lines, commander first
```

Lead with the bend, the turn, and the bar. Then the list. Then at most four cuts you almost made, each tied to a job or a number from the tools.

## Example

User: "Build me a $100 Hapatra."

`reference_deck("Hapatra")` hits. Switch to `nero-tune` on that `decklist`. That still runs `analyze_deck`, `price_decklist`, `find_combos`, and `get_skill("nero-goldfish")`. Do not brew a second Hapatra.
