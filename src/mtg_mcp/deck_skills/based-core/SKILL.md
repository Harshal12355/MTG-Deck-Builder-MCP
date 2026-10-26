---
name: based-core
description: >
  Build and goldfish a 33-card Commander core (one average game = 1/3 of 99)
  before filling the rest of the deck. Locks exact 1-game slot counts for
  lands, ramp, draw, removal, and plan pieces, then tests with analyze_deck
  and simulate_deck at low variance. Use after nero-lines.
---

# Build and test the 33-card 1-game deck first

In an average Commander game you draw about a third of the way into your deck (~33 cards out of 99). Building all 99 cards at once lets a high curve, light card advantage, or short lands hide behind 60 other cards and multiplayer mulligans. Like a 40-card Limited deck, a 33-card Commander core has zero real estate for fluff: every card has high impact, and any flaw shows up immediately when you goldfish it.

If `get_card`, `analyze_deck`, or `simulate_deck` is not in this session, say so and stop.

## Order

```
nero-read + defcat-read + nero-lines
    |
    v
write the 33-card 1-game slot budget (sums to 33)
    |
    v
fill Pile A (best 33 cards) with nero-hunt + defcat-turn (+ defcat-fuel if Bar)
    |
    v
analyze_deck + simulate_deck on Commander + Pile A (34 cards)
    |
    +-- misses ideal turn or curve --> fix Pile A now (before picking 66 more cards)
    +-- hits ideal turn and curve  --> get_skill("based-scale")
```

1. Take the bend and jobs from `nero-read`, the turn window and bar from `defcat-read`, and the win from `nero-lines`.
2. Write the **33-card 1-game slot budget** — every slot is how many of that effect you want to see in ONE average game, and the total must equal **33 cards**:
   - **Lands (10–13)**: 1/3 of the 99-card land target (`10` for 30-land turbo, `11` for 33-land midrange/combo, `12` for 36-land control, `13` for 39-land landfall).
   - **Ramp (2–4)**: timed to the commander's ideal turn (`2` in 33 = `6` in 99 to play a 6-drop on turn 4–5; `4` in 33 = `12` in 99 to play a 4-drop on turn 3).
   - **Veggies per game**:
     - **Card draw (3–4)**: e.g. `3` draw sources in 33 (`9` in 99).
     - **Single-target removal (3)**: e.g. `3` targeted answers in 33 (`9` in 99).
     - **Counterspell / stack protection (1–3)**: `1` in tap-out pseudo-control (`3` in 99), or `3–4` in stack/combo (`9–12` in 99).
     - **Board wipe (0–1)**: `1` sweeper in control (`3` in 99), or `0` when wipes kill your own dorks/tokens.
   - **Plan & engine jobs (remaining slots, 1–2 each)**: every distinct effect your plan needs in one game (e.g. `1` fling, `1` evasion, `1` specific recursion, `1` copy spell, or `1` each of your overlapping combo pieces).
3. Fill **Pile A (33 cards)** using `nero-hunt`, `defcat-turn`, and `defcat-fuel` (only when `Bar` is real). `get_card` on every card before it enters Pile A. Zero 1-of pet cards that do not own a named slot.
4. **Test the 33-card core immediately** before choosing 66 more cards:
   - Format the 34-card test list with an explicit `// Commander` header (or pass `commanders=["..."]`), because the blank-line commander heuristic only triggers on 98–101 card lists:
     ```text
     // Commander
     1 Commander Name

     // Deck
     1 Card 1
     ... (33 cards)
     ```
   - Run `analyze_deck(include_combos=True)` on the 34-card list. Ignore the `must be exactly 100 cards` legality line; check `average_cmc_nonland`, `lands`, `color_pips`, `land_color_sources`, `roles`, and `synergy`.
   - Run `get_skill("nero-goldfish")` (`simulate_deck` with a fixed `seed`, e.g. `seed=33`, and Pile A's `win_lines`). Because the library is only 33 cards, variance is tiny: `opening_hand.kept_seven`, `commander.castable_by_turn` at the ideal turn, and `win_lines` assembly immediately expose a bloated curve or missing ramp.
5. If Pile A misses the commander's ideal turn or stalls, fix the 33-card slot budget and re-sim with the same `seed` now. Do not scale a broken 33-card deck to 99.

## Picture

Confirm with `get_card("Sauron, the Dark Lord")`. Do not skip the lookup.

- `Sauron, the Dark Lord` (`{3}{U}{B}{R}`, 6 MV, Grixis Avatar Horror): opponents casting spells amass Orcs 1; Army combat damage causes the Ring to tempt you; whenever the Ring tempts you, you may discard your hand and draw four cards.
- 1-game plan (33 cards): hit land drops + **2 ramp** sources to cast Sauron turn 4 (turn 5 latest); hide behind the growing Orc Army for 3–4 turns with **3 single-target removal**, **1 counterspell**, and **1 board wipe**; draw **3 card draw** sources; close with **1 evasion** source or **1 fling** effect; trigger Sauron's wheel with **1 Ring tempt** source while **1 cost reducer**, **1 spell copy**, **1 army grower**, **1 specific graveyard recursion**, and flashback spells keep the wheel from punishing you.

## Hand back

```
Core 33:  Lands __ | Ramp __ | Draw __ | Removal __ | Counter __ | Wipe __
Plan 33:  <each 1-of or 2-of job slot in the 33-card deck>
Avg MV:   __ (on the 33-card core)
Sim 33:   Kept 7 __% | Cast by T__ __% (median T__) | Line __% by T__ (seed __)
Pile A:   33 cards verified with get_card
```

Stop only if the user asked for a 33-card core prototype; otherwise proceed immediately to `get_skill("based-scale")`.
