---
name: nero-tune
description: >
  Tune an existing Commander deck against NeRo's principles with the
  mtg-deckbuilder MCP: one plan-fixing swap, then at most four more,
  each tied to a tool number. Use when the user pastes a deck, shares a
  Moxfield, Archidekt, or MTGO link, or asks to tune, cut, upgrade, or
  check a list, including NeRo, _NeRo, budget cEDH, or Bracket 4.
---

# Tune a deck the NeRo way

NeRo (@_NeRo) builds ~$100 high-power Bracket 4. A swap is a 1-for-1 quality bump that still does the deck's jobs. Ten better cards beat one bomb. A staple he plays is a candidate, not an automatic add.

If `reference_principles` is not in this session, read `src/mtg_mcp/data/library/nero/source.json`, or `get_library()` with `PYTHONPATH=src` from the repo root. Same fallback for `reference_deck`, `reference_compare`, and `reference_cards` (`decks.json` via `get_library()`, not by reading the whole file). Say that you used the files. Do not recite principles from memory.

Get the list as text first. Moxfield has no public API. For an Archidekt URL, `archidekt_get_deck` and use its `decklist`. For one of his decks, `reference_deck` and use its `decklist`.

## Order

```
list as text
    |
    v
reference_principles(source="nero")     the test
analyze_deck + price_decklist           the picture
get_card(commander)                     the bend, in one sentence
reference_deck(commander)               his plan, if he built this commander
get_skill based-split                   deal 99 into 3 x 33; spot orphans & uneven slots
find_combos                             in the deck, then one card away
reference_compare(min_decks=3)          his staples this list skips
get_skill nero-goldfish                 calls simulate_deck (Pile A 33 + full 99)
get_skill nero-mana                     only if a color is short
get_card + get_card_printings           before a buy
```

1. `reference_principles(source="nero")`. Grade against the tool result. Do not recite principles from memory.
2. `analyze_deck(include_combos=True)` on the full list. Pass `commanders` if the list does not mark them. Read `bracket` (1–5 + `bracket_path` + `bracket_up_warning`), `power_score` (`0–10` + Speed, Consistency, Saltiness, Interaction, Synergy, Resilience), `school_score` (`NeRo` / `Defcat` / `Based 3x33` + `notes`), and `synergy` (`Enabler × Payoff` axes). `price_decklist` for the real total. The ~$100 cap is the deck, not a per-card cap.
3. `get_card` on the commander. One sentence: the rule it breaks. If the list is built around the surface theme (Rat tribal for Vren, landfall tokens for Tannuk), that is the first cut.
4. `reference_deck` for this commander. Use his plan, mulligan, and `notes.win_lines` as the comparison, not as cards to copy blindly.
4b. `get_skill("based-split")`. Deal the 99 main-deck cards into three 33-card piles (`Pile A / Pile B / Pile C`) by job. Flag uneven `2/2/1` or `11/11/10` splits, `1/0/0` orphan one-offs (`Archmage Emeritus` test), uncounted theme density (`count / 3` per game), and slow random value engines occupying a specific job slot (`Exalted Flamer of Tzeentch` test).
5. `find_combos`. Say what is already in the deck, then what is one card away. Prefer the one-card-away line whose new piece is good alone. A new card uses `get_skill("nero-hunt")`, then `get_skill("defcat-turn")`. A new line uses `get_skill("nero-lines")`. An enabler that does nothing the turn it enters is a cut, even when EDHREC likes it.
5b. `get_skill("defcat-read")` on the commander. `Bar: none` means the swap only has to name its turn: first main, second main, or an opponent's turn. A real bar means `get_skill("defcat-fuel")` before a high mana value add, and that add still does a job the turn you cast it.
6. `reference_compare` with the decklist, `min_decks=3`. Raise `min_decks` for only his real staples. Set `max_price` when the user names a budget. Check each candidate against the deck's jobs.
7. `get_skill("nero-goldfish")`. That skill calls `simulate_deck` (on Pile A's 33-card core + commander and on the full 100-card deck with the same `seed`, plus `track_card_impact=True` to see which cards actually accelerate the commander and win lines). If `simulate_deck` is missing, write "not simulated". Do not invent a percent. **Mandatory after-swap proof**: after picking the swaps, run `compare_decks(before, after)` and rerun `simulate_deck` on the updated 100-card list with the **exact same `seed`**, reporting the before → after delta (`Cast by T_ __% → __%`, color gap, and combo count) while verifying the list stayed inside the user's target Bracket.
8. `get_card` before you name any add or cut. `get_card_rulings` if the line depends on timing. `get_card_printings` before naming a printing to buy.
9. Run `analyze_mana_base` (and `get_skill("nero-mana")` if any color has `deficit > 0` or the Mana Base Grade sits below `B+`). Do not invent a source count.

## Gaps that are not gaps

`roles.note` says the tags are a heuristic. A low count is not an order to add that role.

- The commander already draws when the plan happens (a counter on your creature draws a card). Add more of that action. Do not add a generic draw spell because `card_draw` looks low. Read the gate: `draw_on_cast` resolves with the spell, `draw_on_hit` waits for combat damage, `draw_on_their_spell` waits for an opponent. A hit-draw in a deck with no attackers is a blank.
- A card that puts counters on each creature is the wipe, even when `board_wipe` is 0.
- The 20–25 interaction thumb is for a control shell. A combo-tempo list is not that shell.
- The sideboard is cards they already own. Check it against the jobs before you name a card to buy.
- No `reference_deck` for this commander: use the engine creature's deck for lines only. A card in that deck which fails this commander's jobs stays out.
- His flagship price at capture can sit above the ~$100 thumb. Report both. Do not cut the combo piece to hit $100.
- `no_price_listed` means the total is missing those cards. Say so.

`edhrec_recommendations` comes after the scorecard, with the decklist passed in, and only to show the cookie-cutter shell. Do not lead with those adds. An empty recommendation list means there is nothing to copy.

## Hand back

```
Bend:        <one sentence — does this list actually do that?>
Bracket:     B__ (<label>) · Power __/10 (<tier>) · School __/10 (NeRo __ / Defcat __ / Based __)
Price:       $__   (~$100, or the user's cap)
Avg MV:      __    (thumb from the tool)
Lands:       __ / Karsten says __ (Mana Grade __, tipping point T__)
Interaction: __    (instant ratio __%)
Tutors:      __
Synergy:     __/10 (<signature Enabler x Payoff axes>)
Lines:       in the deck / one card away / pieces that are dead alone
Split 3x33:  uneven slots, 1/0/0 orphans, fake slots, theme per 33 (from based-split)
Curve:       nero-goldfish block + top card_impact accelerators, or "not simulated"
Mana:        color_requirements deficits + pips/sources, or "mana skill not run"

When:        first main | second main | their turn
Bar:         none | what a cast spell sets
Change:      cut X → add Y, because <one number or one combo>
Then:        at most four more, each tied to a number
```

Lead with the one swap that fixes the plan. A card he plays in three or more decks still has to pass the jobs test.

## Example

User pastes a Vren list full of Rat lords.

Bend from `get_card`: Vren is a removal deck that makes Rats. `analyze_deck` shows the removal count. The first swap cuts a lord for a cheap edict. `reference_compare` may offer more edicts. Name one. Do not add a tutor package: his Vren runs zero tutors on purpose.
