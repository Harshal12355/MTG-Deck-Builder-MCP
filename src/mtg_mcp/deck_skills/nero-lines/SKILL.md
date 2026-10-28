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

Rowan's win is one finisher. Vren's win is a pile of edicts.

1. `get_card` the finisher, or `search_cards` the pile. `f:commander` and `id<=` the commander's colors on every query. `order="usd"`. Cap `usd<5` unless the user raised the budget. The cap is the whole deck at about $100.
2. Query shapes:
   - The finisher by name, then the fuel that has to happen first. Rowan: life loss before the tap, generic mana only.
   - A pile: `id<=COLORS o:"sacrifices a creature" mv<=2 usd<3 f:commander`. Swap the oracle words for the effect the win actually counts.
3. Every card has to do something on a turn you do not win. An edict that only matters in the combo is out. Vren's edicts are the win and the removal.
4. **Bracket 3 vs. Bracket 4 Win & Consistency Blueprint:**
   - **Bracket 2 (`~4.8–5.5/10` Fair Core)**: `0` Game Changers, `0` two-card combos.
   - **Bracket 3 (`7.5–8.2/10` High-Consistency Synergy Engine — "Freight Train")**:
     - **Never shoehorn off-theme 4-card combos:** Do NOT jam `Pitiless Plunderer + Shambling Ghast + Chatterfang` into a deck whose commander does not care about creature sacrifice (`Vraska, the Silencer`). Off-theme combo pieces fail the 25th-percentile floor test and cause whiff draws.
     - **Two clean ways to hit `7.5–8.2/10` in Bracket 3:**
       1. **On-Theme Turn 6+ Combos (`2–3` explicit Spellbook combos where every piece triggers the commander):** Use `"S"` (Spicy / Turn 6+) 2-card lines or 3-card loops whose pieces are already fulcrum cards in the deck (`Putrid Goblin + Goblin Bombardment` in `Celes`, or `Karmic Guide + Reveillark`).
       2. **Pure Domino / Density Engine (`engine_momentum_bonus`):** When the deck wins via a Domino/Synergy wave (`Sister Hospitaller -> Metamorphosis Fanatic -> Phyrexian Delver` in `Celes`, or 27 edicts + `Viridian Revel` + `Mirkwood Bats` in `Vraska`), `analyze_deck` awards up to `+0.95` raw points (`engine_momentum_bonus`) when `synergy.score >= 8.0`, `card_draw >= 10` (with `9+` unconditional draw), and `interaction_total >= 10` — paired with **`6` high-tempo tutors** and **`2–3` on-plan Game Changers**.
     - **Tutors in Bracket 3 (`6` = `2` per 33-card pile):** Keep tutor consistency high, but prioritize **1–2 MV tutors** (`Demonic Counsel`, `Wishclaw Talisman`, `Diabolic Intent`, `Lively Dirge`, `Shred Memory`) and **straight-to-battlefield / graveyard / engine tutors** (`Chord of Calling`, `Eldritch Evolution`, `Nature's Rhythm`, `Shared Summons`, `Buried Alive`, `Fauna Shaman`, `Goblin Engineer`) over slow 3+ MV sorcery-to-hand tutors (`Dimir Machinations`, `Diabolic Tutor`, `Case of the Stashed Skeleton`). In Bracket 3, tutors grab your **Engine Fulcrum** on Turn 3–4 and your **Finisher** on Turn 6–7.
   - **Bracket 4 (`8.0–9.0+/10` Optimized — "Race Car")**: overlapping compact 2–3 card explicit Spellbook combos (including early `"R"`/`"P"` 2-card lines), `6–10` fast tutors, `30–33` lands + rituals/fast mana, and `2–4+` Game Changers.

## Overlapping combos & deterministic EDHcheck quotas

Use this for every combo commander AND every high-power (`>= 7.5/10`) build.

1. `search_combos`. Start with `card:"Commander Name"`. Then search the outlet or synergy engine without the commander, so you can see lines that work while the commander is removed. The tool's syntax also includes `cards=2`, `result:"win the game"`, and `id<=COLORS` (same form as the tool's own examples). A query that returns no combos loses one filter and runs again.
2. **Beware the `also_requires` (`template_combos`) 0-point trap:**
   - Commander Spellbook entries that carry `also_requires` (e.g. `also_requires: ["Creature that can tap for mana"]` or `["Sacrifice outlet"]`) are bucketed as `template_combos` and score **0.0 points** on EDHcheck's `combos` meter (`15%` of total Power Score, `20%` of Speed).
   - To guarantee `power_score.components.combos >= 6.4` (`+0.96` to `+1.50` raw points), you MUST include **at least 2–3 explicit Spellbook combos (`also_requires` is empty/null)** where every card name is in the 99 (`two_card_combos` + `three_plus_combos >= 2`).
3. **Deterministic Quotas by Target Bracket & Power Score:**
   - **Bracket 2 (`~4.8–5.5/10` Fair Core)**: `0` Game Changers, `0` two-card combos (`S`, `R`, `P` out).
   - **Bracket 3 (`7.5–8.5/10` High Power / Elite)**:
     - **`2–3` explicit Spellbook combos** (`0` early `"R"`/`"P"` 2-card combos; use `"S"` Spicy 2-card combos like `Chatterfang + Pitiless Plunderer` or 3–4 card explicit loops like `Chthonian Nightmare + Pitiless Plunderer + Shambling Ghast + Greedy Freebooter`).
     - **`6–9` budget tutors/transmutes** (`2–3` per 33-card pile: `Case of the Stashed Skeleton`, `Shred Memory`, `Dimir Machinations`, `Mausoleum Secrets`, `Wishclaw Talisman`, `Demonic Counsel`, `Eldritch Evolution`, `Chord of Calling`, `Shared Summons`).
     - **`2–3` budget WotC Game Changers** (`<= 3` limit: e.g. `Crop Rotation`, `Braids, Cabal Minion`, `Notion Thief`, `Narset, Parter of Veils`, `Tergrid`, `Bolas's Citadel` as budget permits).
   - **Bracket 4 (`8.0–9.0+/10` Optimized)**: any overlapping 2–4 card explicit Spellbook combos (including early `"R"`/`"P"` 2-card lines), `6–12` budget tutors, and `2–4+` Game Changers within budget.
4. Keep a line only when all of these are true:
   - 2 to 4 cards.
   - `get_card` on every piece. On an ordinary turn it does one job from `nero-read`. A piece that is dead alone is out.
   - **Keystone triplication (no `1/0/0` bottleneck)**: a second line shares a piece ("for every A, two or three Bs"), AND any keystone outlet shared across 3+ combos (e.g. 0-mana land sacrifice like `Zuran Orb`) must have functional twins (`Sylvan Safekeeper`, etc.) so the deck does not fold when one card sits in the bottom 66.
   - Most lines still function if the commander is not on the battlefield.
   - Price from `get_card`. One piece over about $15 eats a ~$100 deck. Out, unless the user asked. Thassa's Oracle and Underworld Breach are out unless the user asked for that budget.
5. Three or four lines. After a decklist exists, `find_combos` on it. Verify `in_deck` has `>= 2` explicit combos (`also_requires` null). Say what is already in the deck, then what is one card away. The missing card has to be good alone.

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
