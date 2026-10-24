---
name: based-build
description: >
  Third school on the same list as NeRo and Defcat (Based Deck Department /
  Brother Frog): build and goldfish a 33-card 1-game deck first, then scale
  33 x 3 = 99 with functional twins, or split an existing 99 into three 33-card
  piles to cut orphan 1-offs and slow value engines.
---

# Third school, same list: the 33-card Commander deck

`nero-build` and `nero-tune` are the order. These steps sit inside them. Every card has to pass all three schools: NeRo (the bend, the win, and two jobs the turn you cast it), Defcat (when in the turn it resolves, and the mana-value bar), and Based (the 33-card 1-game blueprint, tested at 33 before scaling `33 × 3 = 99`).

Players who come straight into Magic via Commander skip the lesson of 40-card Limited and 60-card Standard: in a small deck you have zero flexibility, no 60 extra cards or 10 mulligans to hide behind, and when your curve is too high, card advantage is light, or lands are short, you feel it immediately and constantly. In an average Commander game you draw about a third of your deck (~33 cards). Building and testing one 33-card deck first makes the problem small, tangible, and low-variance, then replicating it two more times makes the 99-card deck a reliable "silly goose" instead of a once-a-year "pigeon".

If `get_card`, `analyze_deck`, or `simulate_deck` is not in this session, say so and stop.

## Order

```
new build (nero-build)                           existing 99 (nero-tune)
    |                                                |
    v                                                v
nero-read + defcat-read + nero-lines             analyze_deck + nero-read + defcat-read
    |                                                |
    v                                                v
get_skill based-core                             get_skill based-split
  - lock 33-card 1-game slot budget                - deal 99 into 3 x 33 (Pile A / B / C)
  - fill Pile A (33 cards) via nero-hunt           - flag uneven splits (2/2/1, 11/11/10)
    + defcat-turn (+ defcat-fuel if Bar)           - flag 1/0/0 orphans (Archmage Emeritus)
  - analyze_deck + nero-goldfish on 33+cmdr        - flag value in specific slots (Exalted Flamer)
    |                                              - benchmark Pile A (33) vs full 99 in simulate_deck
    v                                                |
get_skill based-scale                                v
  - replicate Pile A x3 -> Pile B + Pile C       feed the worst offender into nero-tune swaps
  - nero-mana + 99-card analyze + price
  - nero-goldfish on 99 (compare to 33-card sim)
```

1. **New build**: after `nero-read`, `defcat-read`, and `nero-lines`, run `get_skill("based-core")`. Lock the 33-card 1-game slot budget, fill Pile A (33 cards + commander), and run `analyze_deck` + `get_skill("nero-goldfish")` on that 34-card list before picking 66 more cards.
2. **Scale `33 → 99`**: once the 33-card core hits its ideal turn and curve in `simulate_deck`, run `get_skill("based-scale")`. Give every slot in Pile A two functional twins in Pile B and Pile C (`1 → 3`, `2 → 6`, `3 → 9`, `11 lands → 33 lands`). Re-run `nero-goldfish` on the 99 with the same `seed` and compare against the 33-card benchmark.
3. **Tune an existing 99**: run `get_skill("based-split")` inside `nero-tune`. Deal the 99 into three 33-card piles by job. Cut `1/0/0` orphans (`Archmage Emeritus` when magecraft isn't the core focus), fix uneven `2/2/1` veggie/land splits, count theme density per 33 cards, and replace slow random value engines (`Exalted Flamer of Tzeentch`) with the specific card that slot needs.
4. Do not stop here. Finish `nero-build` or `nero-tune`: `nero-mana`, `analyze_deck`, `price_decklist`, `find_combos`, `nero-goldfish`, `edhrec_recommendations`, `archidekt_popular_cards`, and `moxfield-primer`.

## Hand back

Use the block from `nero-build` (filling `Core 33`) or `nero-tune` (filling `Split 3x33`). Do not write a separate report.

## Example

User: "Build Sauron, the Dark Lord."

`based-core` locks 33 slots for one game (lands + 2 ramp for turn 4–5 Sauron, 3 draw, 3 targeted removal, 1 counter, 1 wipe, 1 spell copy, 1 army grower, 1 fling, 1 Ring tempt, 1 evasion, 1 cost reducer, 1 specific recursion, flashback glue) and goldfishes the 34-card list first. `based-scale` triplicates each slot to 99 (`2 ramp → 6`, `3 draw → 9`, `1 fling → 3`) and checks that the 99-card goldfish stays on the 33-card curve.
