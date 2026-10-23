---
name: nero-lines
description: >
  Find the win for a ~$100 Bracket 4 deck: one spell, a pile of the same
  effect, or overlapping 2-4 card combos whose pieces are good alone.
  Use after nero-read, and when a tune needs a new line. Search comes
  from search_combos and search_cards, not from memory.
---

# Find the win lines

The win shape comes from `nero-read`. If you do not have that block, `get_skill("nero-read")` first.

If `search_cards` or `search_combos` is missing, say so and stop. Do not invent a combo.

## One spell, or a pile

Rowan's win is one finisher. Vren's win is a pile of edicts. Both stop here.

1. `get_card` the finisher, or `search_cards` the pile. `f:commander` and `id<=` the commander's colors on every query. `order="usd"`. Cap `usd<5` unless the user raised the budget. The cap is the whole deck at about $100.
2. Query shapes:
   - The finisher by name, then the fuel that has to happen first. Rowan: life loss before the tap, generic mana only.
   - A pile: `id<=COLORS o:"sacrifices a creature" mv<=2 usd<3 f:commander`. Swap the oracle words for the effect the win actually counts.
3. Every card has to do something on a turn you do not win. An edict that only matters in the combo is out. Vren's edicts are the win and the removal.
4. Say `no combo package` and stop. Do not open Spellbook for a second plan.

## Overlapping combos

Use this when the win shape says overlapping combos.

1. `search_combos`. Start with `card:"Commander Name"`. Then search the outlet without the commander, so you can see lines that work while the commander is removed. The tool's syntax also includes `cards=2`, `result:"win the game"`, and `id<=COLORS` (same form as the tool's own examples). A query that returns no combos loses one filter and runs again.
2. Keep a line only when all of these are true:
   - 2 to 4 cards.
   - `get_card` on every piece. On an ordinary turn it does one job from `nero-read`. A piece that is dead alone is out.
   - A second line shares a piece. For every A, two or three Bs.
   - Most lines still function if the commander is not on the battlefield.
   - Price from `get_card`. One piece over about $15 eats a ~$100 deck. Out, unless the user asked. Thassa's Oracle and Underworld Breach are out unless the user asked for that budget.
3. Three or four lines. After a decklist exists, `find_combos` on it. Say what is already in the deck, then what is one card away. The missing card has to be good alone.

## Hand back

```
Shape:    one spell | a pile | overlapping combos
Lines:    A + B + C — B does <job> alone; A is also in line 2
Without:  lines that still work if the commander is removed
Dead:     pieces that do nothing alone
Skipped:  the popular line you cut, and whether it was the price or a dead piece
```

`no combo package` replaces the Lines row when the win is one spell or a pile. Name the finisher or the effect, and two or three cards that make it happen.

## Example

Vren's shape is a pile. `search_cards` with `id<=ub o:"sacrifices a creature" mv<=2 f:commander`. Hand back `no combo package` and the edicts `get_card` confirmed. Do not add Dualcaster lines to a Rat deck that wins by exiling what dies.

A combo commander uses `card:"Dualcaster Mage"` and keeps Twinflame only if `get_card` says Twinflame does a job on a turn you do not combo, and a second copy effect shares Dualcaster.
