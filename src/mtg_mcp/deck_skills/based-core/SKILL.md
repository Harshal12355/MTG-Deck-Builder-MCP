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
   - **Lands (10–13, matched to target Bracket)**:
     - **Bracket 4 Turbo/Combo (`10–11` in 33 = `30–33` in 99)**: fast mana, rituals, and avg MV `<= 2.1`.
     - **Bracket 3 Synergy Engine (`12` in 33 = `36` in 99, including 1 MDFC spell-land per pile)**: Bracket 3 games go 7–9 turns (`6+ turns` expected). Never starve a Bracket 3 engine at 10–11 lands (`30–33`) or it will brick on Turn 4–5 land drops.
     - **Landfall (`13` in 33 = `39` in 99)**.
   - **Ramp (3–4)**: timed to the commander's ideal turn (`3–4` permanent ramp sources in 33 = `9–12` in 99). In Bracket 3, prefer permanent rocks/dorks/land-ramp over one-shot rituals (`Dark Ritual`) unless the commander storms off the turn it taps.
   - **Veggies per game (Zero Whiff / High Floor)**:
     - **Card draw (4 in 33 = 12 in 99)**: at least **3 of the 4** in Pile A (`9+` in 99) MUST be **unconditional / self-starting draw** (`Night's Whisper`, `Ripples of Undeath`, `Black Market Connections`, `Dark Confidant`, `Mystic Remora`, `Talion`) — NEVER fill more than 1 slot per 33 (`<= 3` in 99) with conditional sacrifice-a-creature draw (`Village Rites`, `Altar's Reap`, `Midnight Reaper`) unless the commander creates creature tokens on its own.
     - **Single-target removal (3)**: e.g. `3` targeted answers in 33 (`9` in 99).
     - **Counterspell / stack protection (1–3)**: `1–2` in midrange/engine (`3–6` in 99), or `3–4` in stack/combo (`9–12` in 99).
     - **Board wipe (1)**: `1` one-sided or synergistic sweeper in 33 (`3` in 99), or `0` in pure dork turbo.
     - **Tutors (`2` in 33 = `6` in 99 for B3/B4)**: use **1–2 MV tutors** (`Demonic Counsel`, `Wishclaw Talisman`, `Diabolic Intent`, `Lively Dirge`, `Shred Memory`) or **straight-to-battlefield / graveyard tutors** (`Chord of Calling`, `Eldritch Evolution`, `Nature's Rhythm`, `Shared Summons`, `Buried Alive`, `Fauna Shaman`, `Goblin Engineer`) that find your **Engine Fulcrum** on Turn 3–4 AND your **Win Finisher** on Turn 6–7. Avoid `>= 3` slow 3-MV sorcery-to-hand tutors (`Dimir Machinations`, `Case of the Stashed Skeleton`).
   - **Plan, Fulcrum Engines & Finishers (remaining slots, 1–2 each; `<= 5` situational/6+ MV cards across the 99)**: every card must pass the **25th-percentile floor test** (useful even when you are behind).
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
