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
         get_skill based-core            lock 33-card 1-game slots; fill Pile A (33)
         get_skill nero-hunt             veggies first, then double-duty cards
         get_skill defcat-turn           rescore those keeps
         get_skill defcat-fuel           only when the bar is real
         analyze_deck + nero-goldfish    test the 33-card core (34 cards) first
         get_skill based-scale           triplicate Pile A x3 -> 99 (zero 1/0/0 orphans)
         get_skill nero-mana
         analyze_deck + price_decklist + find_combos
         get_skill nero-goldfish        calls simulate_deck on 99 (same seed as 33)
         edhrec_recommendations + archidekt_popular_cards
         get_skill moxfield-primer          tagged list + markdown primer
```

1. `reference_principles(source="nero")`. Grade the list against what the tool returns. Do not recite principles from memory.
2. `get_card` on the commander. Write the rule it breaks in one sentence. Vren is a removal deck that makes Rats. If you cannot name the bend, stop and say so.
3. `reference_deck` with the commander name. A hit means start from his `decklist` and his `notes.win_lines`. Say which deck. Then switch to the tune skill's scorecard on that list.
4. No hit: `get_skill("nero-read")`, then `get_skill("defcat-read")`. NeRo jobs and the win shape are the test for every later card. Defcat adds the turn that card wants, and a mana-value bar when the commander compares one. `Bar: none` is a complete answer. If you cannot name the bend, stop.
5. `get_skill("nero-lines")` before any synergy card. A one-spell or edict-pile win does not get a combo package.
6. `get_skill("based-core")`. Lock the 33-card 1-game slot budget (one average Commander game = 1/3 of 99). Fill **Pile A (the first 33 cards)** using `get_skill("nero-hunt")`, then `get_skill("defcat-turn")` on those keeps. A keep that is blank on the turn the deck acts is a cut. Draw, ramp, and interaction first. Then cards that do a job and the plan. `reference_cards` is inside the hunt skill.
6b. `get_skill("defcat-fuel")` only when the bar is real. A fuel card still does a NeRo job the turn you cast it. `Bar: none` means no fuel package.
6c. Test **Pile A + commander (34 cards)** with `analyze_deck` and `get_skill("nero-goldfish")` (`simulate_deck`) before picking 66 more cards. Fix curve or ramp gaps in the 33-card core first, then run `get_skill("based-scale")` to replicate every slot two more times (`33 × 3 = 99`, Piles B and C) with functional twins — no `1/0/0` orphans (`Archmage Emeritus` test) and no slow random value engines in specific slots (`Exalted Flamer of Tzeentch` test).
7. `get_card` (and `get_card_rulings` if the line depends on timing) before a card is in the list. `f:commander` and `id<=` the commander's colours on every `search_cards`.
8. Lands last, then `get_skill("nero-mana")` (`analyze_mana_base` + `search_lands`) on the finished list. Count follows the plan and Karsten's regression (`recommended_land_count`), not a rigid 38.
9. `analyze_deck(include_combos=True)`, `price_decklist`, `find_combos`, `find_tokens`, then `get_skill("nero-goldfish")` (`simulate_deck` with `track_card_impact=True`) on the full 100-card list with the same `seed` as the 33-card core test. Copy its hand-back into Curve, and report `bracket` (1–5), `power_score` (0–10), `school_score` (NeRo / Defcat / Based 3x33), and `synergy` (`Enabler × Payoff`). Do not invent a percent. If `simulate_deck` is missing, write "not simulated".
10. `edhrec_recommendations` with `budget="budget"` and the decklist, and `archidekt_popular_cards`. Both show the shell. Neither is the shopping list. `get_card_printings` before naming a printing to buy. `price_decklist` again before telling anyone to buy. Default budget is about $100 for the deck.
11. `get_skill("moxfield-primer")` unless the user said they do not want a primer or Moxfield tags. That skill owns the tagged list and the copy-paste primer.

`deckbuilding_template` is the wrong ruler here. Land count, interaction, and tutors come from `reference_principles` rules of thumb and from `analyze_deck`. `edhrec_recommendations` is a check for the cookie-cutter shell, not the shopping list. Call it with `budget="budget"` only after the list exists, and only to see what everyone else plays.

## Hand back

```
Bend:     <one sentence>
When:     first main | second main | their turn
Bar:      none | what a cast spell sets
Jobs:     1 …  2 …  3 …  4 …
Fuel:     none | printed MV, mana you pay
Core 33:  <slot budget in 33, scaled x3 to 99; 33-card vs 99-card sim>
Started:  his <deck name>   |   new list
Bracket:  B__ (<label>) · Power __/10 (<tier>) · School __/10 (NeRo __ / Defcat __ / Based __)
Synergy:  __/10 (<signature Enabler x Payoff axes>)
Price:    $__   (~$100)
Avg MV:   __    (thumb from the tool)
Lands:    __    (Mana Grade __, tipping point T__, why this count)
Lines:    <2–4 overlapping lines; which pieces are dead alone>
Curve:    nero-goldfish block (kept 7, cast by ideal turn, each line, top card_impact accelerators)

List:     plain `1 Card Name` lines, commander first
Moxfield: moxfield-primer blocks (tagged list + markdown), when step 11 ran
```

Lead with the bend, the turn, and the bar. Then the list (or the Moxfield tagged list if step 11 ran). Then at most four cuts you almost made, each tied to a job or a number from the tools. Put the full primer after the list when step 11 ran.

## Example

User: "Build me a $100 Hapatra."

`reference_deck("Hapatra")` hits. Switch to `nero-tune` on that `decklist`. That still runs `analyze_deck`, `price_decklist`, `find_combos`, and `get_skill("nero-goldfish")`. Do not brew a second Hapatra.
