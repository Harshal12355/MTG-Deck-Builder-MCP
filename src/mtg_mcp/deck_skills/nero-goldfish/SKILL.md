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
3. `simulate_deck` on the main list, commander passed if the list does not mark it. Default `trials` is fine. Set `seed` when you compare a before and an after.
4. Read the result, not a vibe:
   - `opening_hand.kept_seven` and `average_mulligans`
   - `commander.castable_by_turn` at the ideal turn, and `median_turn`
   - each line's `assembled_by_turn` at the turn the plan wants to win
5. Quote `assumptions` from the result. Mana is counted by amount, not color. A deck that is short a color can still "cast" the commander here. If pips per source are lopsided, say the cast rate ignores that and `get_skill("nero-mana")`.
6. Do not set `extra_cards_per_turn` to fake a commander who draws off a combat, a counter, or a free spell off the top. The goldfish does not play those triggers. Leave it at 0 unless the user asks for a draw-engine guess, and label the guess.
7. A comparison commander (a mana-value bar, the first spell each turn) still gets this sim. Report the commander cast rate, and say the free casts are not in it. When `nero-lines` said `no combo package`, pass no `win_lines` and write `Line: no combo package`.

## Hand back

```
Ideal turn:   3
Kept 7:       __%
Cast by then: __%    median turn __
Line:         <name> __% by turn __
Color:        goldfish ignored color. Short colors, if any: __
```

One sentence on whether the list is fast enough for the plan. If a swap changes the list, rerun with the same seed and show the two percents side by side.

## Example

Ool costs 4, so the ideal turn is 3. Read `castable_by_turn` for turn 3. Her draw trigger is not in the goldfish. Leave `extra_cards_per_turn` at 0. If green is 35 pips on 19 sources, the cast percent is the colorless upper bound.
