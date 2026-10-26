---
name: nero-goldfish
description: >
  Goldfish a Commander deck with simulate_deck: keep rate, chance the
  commander is cast by the ideal turn, and chance each win line is assembled
  by turn. Use when the user asks how fast a deck is, what to mulligan for,
  or for a curve check. The result is not a win rate.
---

# Goldfish the NeRo way

The ideal turn comes from the commander's mana value and the plan. Hapatra is turn 2. A 4-mana commander is turn 3. The goldfish checks whether the deck actually gets there.

If `simulate_deck` is not in this session, say "not simulated" and stop. Do not invent a percent. Do not write a replacement simulator.

## Order

```
get_card(commander)          ideal turn = the turn they can cast it with T1 + T2 ramp
win lines                    find_combos "in_deck", or his notes.win_lines
simulate_deck                same seed when comparing two lists
```

1. `get_card` the commander if you do not already have the mana value. One sentence: the turn the deck wants the commander down.
2. Win lines are the combos `find_combos` already found in the deck, or `notes.win_lines` from his deck. Pass them as `win_lines`: a list of card-name groups. `A | B` means either card fills that slot.
3. `simulate_deck` on the main list, commander passed if the list does not mark it. Default `trials` is fine. Pass `track_card_impact=True` on the 99-card run to see single-card knockout attribution (which cards in the 99 actually accelerate the commander and win lines). Pass `mulligan_targets` (e.g. `[{"category": "land", "count": 3, "by_turn": 3}, {"category": "ramp", "count": 1, "by_turn": 2}, {"category": "interaction", "count": 1, "by_turn": 3}]`) when checking a mulligan plan. Set `seed` when you compare a before and an after, or when comparing a **33-card core (`based-core` / `based-split` Pile A, 34 cards with commander)** against the **full 99-card deck (`based-scale`, 100 cards)**. Always include `// Commander` or pass `commanders=[...]` on a 33-card core so the commander is not parsed as main deck.
4. Read the result, not a vibe:
   - `opening_hand.kept_seven` and `average_mulligans` (plus `mulligan_strategy.success_rate` when `mulligan_targets` was passed)
   - `commander.castable_by_turn` at the ideal turn, and `median_turn`
   - `commander.castable_ignoring_color_by_turn` at that same turn
   - `development.median_hand_by_turn` and `development.follow_up_by_turn` at that turn
   - each line's `assembled_by_turn` (mana can cast it) and `seen_by_turn` (names have shown up)
   - `card_impact` top accelerators when `track_card_impact=True`
5. Quote `assumptions` from the result. `castable_by_turn` pays colored pips. **10% Color-Screw / Tapland Alarm**: when `castable_ignoring_color_by_turn - castable_by_turn >= 0.10` (10 percentage points) at the ideal turn, or `classified.tapped_lands` has more than `4` lands in a 3+ color deck, the mana base is choking the commander — run `get_skill("nero-mana")` immediately and cut slow taplands before cutting spells. A high cast rate with a shrinking `median_hand_by_turn` and a low `follow_up_by_turn` means the deck spent its hand on mana and has nothing left to cast.
6. Do not set `extra_cards_per_turn` to fake a commander who draws off a combat, a counter, or a free spell off the top. The goldfish does not play those triggers. A spell whose text draws cards when you cast it is already counted. Leave the knob at 0 unless the user asks for a draw-engine guess, and label the guess.
7. A comparison commander (a mana-value bar, the first spell each turn) still gets this sim. Report the commander cast rate, and say the free casts are not in it. When `nero-lines` said `no combo package`, pass no `win_lines` and write `Line: no combo package`.

## Hand back

```
Ideal turn:   3
Kept 7:       __%
Cast by then: __%    median turn __
Ignoring color: __%
Hand:         median __ cards    follow-up spell cast __%
Line:         <name> __% payable by turn __    (__% seen)
```

One sentence on whether the list is fast enough for the plan. If cast and ignoring-color differ, the gap is the mana base. If the hand median is falling and follow-up is low, the deck is spending its cards on mana. If a swap changes the list, rerun with the same seed and show the two percents side by side.

## Example

Ool costs 4, so the ideal turn is 3. Read `castable_by_turn` for turn 3, then `castable_ignoring_color_by_turn`. Her draw trigger is not in the goldfish. Leave `extra_cards_per_turn` at 0. If those two percents differ, run `nero-mana`.
