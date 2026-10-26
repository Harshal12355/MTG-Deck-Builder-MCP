---
name: based-split
description: >
  Split an existing 99-card Commander deck into three 33-card mini-decks
  (Pile A, Pile B, Pile C) to expose uneven role counts, orphan 1-offs
  (Archmage Emeritus), uncounted theme density, and slow value engines
  (Exalted Flamer of Tzeentch) hiding in specific job slots. Use inside nero-tune.
---

# Audit a 99-card deck by splitting it into 3 × 33

Even a deck you think is solved hides sloppy counts, pet 1-offs, and vague value cards behind 99 slots. In an average game you only see ~33 cards (1/3 of the deck). Dealing an existing 99-card list into three 33-card mini-decks (`Pile A`, `Pile B`, `Pile C`) forces every card to justify its slot in a single game and exposes why a deck feels inconsistent.

If `analyze_deck`, `get_card`, or `simulate_deck` is not in this session, say so and stop.

## Order

```
analyze_deck + get_card(commander) + nero-read + defcat-read
    |
    v
deal the 99 main-deck cards into Pile A (33), Pile B (33), Pile C (33) by job
    |
    v
run the 5 checks:
  1. uneven splits (2/2/1 or 11/11/10)
  2. orphan 1-offs (1/0/0 — Archmage Emeritus test)
  3. keystone bottlenecks (3+ combos sharing a single 1/0/0 outlet like Zuran Orb)
  4. theme density per 33 (Ring tempt / flashback count ÷ 3)
  5. generic value in a specific slot (Exalted Flamer of Tzeentch test)
    |
    v
simulate_deck on Pile A (best 33 + commander) vs Full 99 (same seed)
    |
    v
hand the #1 offender to nero-tune as the plan-fixing swap
```

1. Group the 99 main-deck cards by the actual jobs from `nero-read` and `analyze_deck`: Lands, Ramp, Draw, Targeted Removal, Counterspells, Board Wipes, and each specific plan job (e.g. fling, evasion, Ring tempt, recursion, sac outlet, combo piece).
2. Deal each job evenly across **Pile A (best 33)**, **Pile B (second 33)**, and **Pile C (weakest 33)**:
   - Put the lowest-MV, highest-impact card of each triplet into Pile A, the second into Pile B, and the third into Pile C.
3. Check the five diagnostics from the 33-card exercise:
   - **Uneven splits (`2/2/1` or `11/11/10`)**: Where Pile C is missing a land, a ramp source, a counterspell, or a draw spell because the 99 did not have a clean `3×` multiple for that job.
   - **Orphan 1-offs (`1/0/0` — the `Archmage Emeritus` trap)**: Confirm `get_card("Archmage Emeritus")` when referencing the picture. Any card sitting at `1/0/0` with no functional twins in Piles B and C is a once-a-year "pigeon" card. Either **cut the `1/0/0` orphan** to finish an uneven `2/2/1` core slot, or **add two twins (`1/1/1`)** if that effect is actually the plan.
   - **Keystone bottlenecks (`1/0/0` combo outlets)**: Even if coarse roles (`Lands`, `Ramp`, `Draw`, `Removal`) score `10/10`, check `find_combos` for any single card that gates 3+ combos or the commander's engine (e.g. `Zuran Orb` as the sole 0-mana repeatable land sacrifice outlet across 10 combos). A `1/0/0` keystone must get at least one or two functional twins (`Sylvan Safekeeper`, etc.) in Piles B/C.
   - **Theme density per game (the Ring-tempt / Flashback check)**: Divide each theme count by 3 (`count / 3 = average copies seen per game`). Spot where you threw in a random pile of theme cards without knowing how many show up in a 33-card game, or where a synergy you rely on is only at `1` or `2` copies across 99 (`0.3–0.6` per game).
   - **Generic value vs. specific slot (`Exalted Flamer of Tzeentch` trap)**: Confirm `get_card("Exalted Flamer of Tzeentch")` when referencing the picture. When a card is forced to occupy a named slot in Pile B or Pile C (such as `graveyard recursion`), check with `get_card` whether it performs that specific job on the turn you cast it, or whether it is a slow/random value engine (Flamer returns a random instant or sorcery at upkeep) disguising a missing recursion spell.
4. **Fast 33-card vs. 99-card Goldfish diagnostic**:
   - Build a 34-card test list from `// Commander\n1 <Commander>\n\n// Deck\n<Pile A's 33 cards>` and run `simulate_deck` on both **Pile A (34 cards)** and the **full 100-card deck** with the **same `seed`**.
   - If Pile A casts the commander on time and assembles lines cleanly while the 99 lags behind, Piles B and C have curve bloat or missing ramp/lands.
5. Turn the sharpest finding (`1/0/0` orphan cut, `Exalted Flamer`-style fake slot swap, or uneven `2/2/1` veggie fix) into the lead swap in `nero-tune`.

## Hand back

```
Split 3x33:  Lands __/__/__ | Ramp __/__/__ | Draw __/__/__ | Removal __/__/__
Uneven:      jobs that split 2/2/1 or 1/1/0 across Piles A/B/C
Orphans:     1/0/0 one-offs with no twins in B/C (cut, or promote to 1/1/1)
Fake slot:   value engine sitting in a specific job slot (Exalted Flamer check)
Theme/33:    <theme> __ in 99 = __ per 33-card game
Sim A vs 99: Pile A cast by T__ __% vs Full 99 __% (seed __)
```

## Example

User pastes a 99-card `Sauron, the Dark Lord` spellslinger list.

`based-split` deals the 99 into three 33-card piles. It catches: (1) lands at `12/11/11` and counterspells at `1/1/0` (Pile C is short a counter and a ramp piece), (2) `Archmage Emeritus` sitting alone at `1/0/0` outside the core fling/wheel plan, (3) `Exalted Flamer of Tzeentch` occupying Pile C's recursion slot with random upkeep recursion instead of targeted recursion, and (4) Ring-tempt + flashback counts per 33 cards. The lead swap cuts the `1/0/0` orphan or random Flamer for the specific recursion/counter slot Pile C is missing.
