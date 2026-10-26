---
name: based-scale
description: >
  Scale a tested 33-card Commander core into a 99-card deck (33 x 3 = 99) by
  giving every slot two functional twins (Pile B and Pile C). Makes the deck a
  reliable "silly goose" instead of a once-a-year "pigeon". Use after based-core.
---

# Scale 33 to 99: silly goose, not a pigeon

Players think they want randomness in Commander when what they really want is uniqueness — being a silly goose doing silly goose things. A unique interaction is only cool if it happens reliably every game instead of once a year ("Peak High School" stories about the one game the deck worked). Once `based-core` (Pile A, 33 cards) passes its goldfish and curve check, replicate every slot two more times (`33 × 3 = 99`) so all three 33-card piles execute the exact same game plan.

If `based-core` has not run yet, load `get_skill("based-core")` first. If `get_card`, `search_cards`, `analyze_deck`, or `simulate_deck` is missing, say so and stop.

## Order

```
Pile A (tested 33-card core)
    |
    v
for each slot in Pile A, find 2 functional twins -> Pile B (33) + Pile C (33)
    |
    v
every twin passes nero-hunt + defcat-turn (+ defcat-fuel if Bar)
    |
    v
cut 1/0/0 orphans (Archmage Emeritus) and vague value (Exalted Flamer of Tzeentch)
    |
    v
nero-mana + analyze_deck + price_decklist + find_combos on full 99+cmdr (100 cards)
    |
    v
nero-goldfish on 100 cards with the SAME seed as based-core (compare 33 vs 99)
```

1. Multiply every slot in `based-core` by 3 (`Pile A` = Core 33, `Pile B` = Second 33, `Pile C` = Third 33):
   - `1` slot in 33 → `3` cards in 99 (`1/1/1` across A/B/C — ~1 seen per average game)
   - `2` slots in 33 → `6` cards in 99 (`2/2/2` across A/B/C — ~2 seen per average game)
   - `3` slots in 33 → `9` cards in 99 (`3/3/3` across A/B/C — ~3 seen per average game)
   - `11` lands in 33 → `33` lands in 99 (`12` → `36`, `10` → `30`, `13` → `39`)
2. Find the two functional twins for each nonland slot with `reference_cards` and `search_cards` (`f:commander` and `id<=` the commander's colors). `get_card` on every twin before it goes into Pile B or Pile C.
3. Every twin must pass four checks:
   - **Same job and turn window**: passes `nero-hunt` (works the turn you cast it) and `defcat-turn` (resolves in the same window as Pile A's card).
   - **Same curve weight**: do not replace a 1–2 MV card in Pile A with a 4–5 MV twin in Pile C. That bloats the 99-card curve and breaks the 33-card goldfish benchmark.
   - **Specific job over generic value (`Exalted Flamer of Tzeentch` test)**: if the slot in Pile A is specific recursion, Pile B and Pile C must also be specific recursion — not a slow random value engine.
   - **No `1/0/0` orphans (`Archmage Emeritus` test)**: do not drop a random 1-of into Pile C because you ran out of ideas. Either the effect owns a `1/1/1` triplet across all three piles, or it is out.
4. **Overlapping combos and keystone triplication across `3 × 33`**:
   - When `nero-lines` chose overlapping combos, spread interchangeable pieces (`A1 | A2 | A3` and `B1 | B2 | B3`, or the combo piece in Pile A plus 2 tutors/transmutes at the same MV in Piles B and C) so every 33-card slice can assemble the win.
   - **Never leave a keystone outlet at `1/0/0`**: if 3+ lines depend on one specific sub-effect (e.g. a 0-mana land sacrifice outlet like `Zuran Orb`), give it functional twins in Piles B and C (`Sylvan Safekeeper`, etc.) or instant-speed tutors at the same MV.
5. Combine `Commander + Pile A + Pile B + Pile C` (`100` cards total). Run `get_skill("nero-mana")` (`analyze_mana_base` + `search_lands`), `analyze_deck(include_combos=True)`, `price_decklist(budget_target=100)`, `find_combos`, `find_tokens`, and `get_skill("nero-goldfish")` (`simulate_deck` with `track_card_impact=True`) with the **same `seed`** used in `based-core`.
6. Compare the 99-card goldfish against the 33-card core benchmark:
   - `kept_seven` and `commander.castable_by_turn` at the ideal turn should stay within a few points of the 33-card run.
   - Pass interchangeable twins as `"Card A1 | Card A2 | Card A3"` in `win_lines` so `simulate_deck` measures the true triplicated assembly rate.

## Pictures

Confirm both with `get_card`. Do not skip the lookup because this file names them.

- **`Archmage Emeritus`** (`{2}{U}{U}`, 4 MV): draws a card whenever you cast or copy an instant or sorcery. Great card in isolation, trap when it sits as a `1/0/0` one-off outside the core 33-card focus. Either build a `1/1/1` magecraft slot across all three piles or cut the orphan.
- **`Exalted Flamer of Tzeentch`** (`{2}{U}{R}`, 4 MV): at the beginning of your upkeep, returns an instant or sorcery card **at random** from your graveyard to your hand, and deals 1 damage to each opponent on instant/sorcery cast. A slow, random value engine fails a slot that needs **specific recursion** on the turn you cast it.

## Hand back

```
Grid 3x33:  Slot/Job | Pile A (Core) | Pile B (Twin 2) | Pile C (Twin 3)
Theme/33:   <theme/mechanic> __ per 33 (__ in 99 = ~__ seen per game)
Orphans:    0 (all nonland slots triplicated 1/1/1, 2/2/2, or 3/3/3)
Sim 33→99:  Kept 7 __% → __% | Cast by T__ __% → __% | Line __% → __% (same seed)
```
