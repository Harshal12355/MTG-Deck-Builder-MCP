---
name: defcat-build
description: >
  Second school on the same list as NeRo: when in the turn a card
  wants to resolve, and a mana-value bar when the commander sets one.
  Use on every build and every tune, after nero-read and nero-hunt.
  Fuel only when the bar is real.
---

# Second school, same list

`nero-build` is the order. These steps sit inside it. A card has to pass both schools.

If `get_card` is not in this session, say so and stop.

## Order

1. `get_skill("defcat-read")` after `nero-read`. `Bar: none` is complete when the commander does not compare mana value, reveal the top, or trigger on the first spell. Still name the turn: first main, second main, or an opponent's turn.
2. `get_skill("defcat-turn")` after `nero-hunt`. Rescore the keeps. A keep that is blank on the turn the deck acts is a cut.
3. `get_skill("defcat-fuel")` only when the bar is real. Each fuel card still does a job from `nero-read` the turn you cast it.
4. When the bar is real, the hand is interaction and the payoffs sit in the library under that bar. Bracket 2–3 keeps the top random. A higher bracket adds one dial and names it: untap on an opponent's turn, an extra trigger, or a tutor to the top. `get_card_rulings` before you claim the extra trigger works with "first spell each turn."
5. Do not stop here. Finish `nero-build`: `get_skill("nero-mana")`, `analyze_deck`, `price_decklist`, `find_combos`, `get_skill("nero-goldfish")`, `edhrec_recommendations`, `archidekt_popular_cards`. The goldfish calls `simulate_deck`. It does not see free casts. Run it anyway. When the bar is real, say the cast rate is the commander, not the free spells.

## Hand back

Use the block from `nero-build`, including the `nero-goldfish` curve. Fill `When`, `Bar`, and `Fuel`. Do not write a second list.

## Example

User: "Build a $100 Rowan."

`nero-read` names the bend. `defcat-read` writes `Bar: none` and `When: your turn, after the life is lost`. `defcat-fuel` stops. `defcat-turn` checks the finisher. Then `nero-mana`, `price_decklist`, and `nero-goldfish` still run. One list.
