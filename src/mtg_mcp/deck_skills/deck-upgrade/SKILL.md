---
name: deck-upgrade
description: >
  Diagnose a pasted Commander list, then lock one goal, one win, and a
  budget with the user before any upgrade. Use when the user pastes a
  deck, shares a file, or sends a Moxfield, Archidekt, or MTGO link, or
  asks to upgrade, tune, or rebuild a list to a budget.
---

# Upgrade only after the plan is clear

A pasted list already has a plan, even when that plan is a mess. Read it. Show how the pieces fit. Agree on the goal, the win, and the budget. Then build. A paste is not a yes.

If `get_skill` or `price_decklist` is missing, say so and stop. Do not invent prices or a win.

The budget is the number they named. They did not name one: the cap is what `price_decklist` says this list costs today. Say that once. Do not silently switch the cap to $100.

## Order

```
list as text
    |
    v
get_skill nero-tune          the read. scorecard only. no adds.
fit table                    win, setup, mana, interaction, seeing cards
2 plans, one question, stop
    |
    +-- user picks --> locked card, one question: build?
    |
    +-- same win ----> get_skill nero-tune     the build
    +-- new win -----> get_skill nero-build
    |
    v
price_decklist again
fits | tight | does not fit
```

1. Get the list as text. `archidekt_get_deck` for an Archidekt URL. Moxfield has no public API.
2. `get_skill("nero-tune")` and follow its **Read** section. You need the scorecard: bend, price, mana, lines, the 3×33 split, the goldfish. `Change` stays `waiting on the lock`.
3. `get_skill("nero-read")` and `get_skill("defcat-read")` if the scorecard does not already have Bend, When, and Bar. `Bar: none` is a complete answer.
4. Fill the fit table from those tool results. Then show two plans. Ask one question. Stop. Do not call `nero-build` or the tune skill's build in this turn.

## How it has to fit

The win is the center. Four pieces around it have to work on the same turn the win happens. Fill each from a tool. A blank cell is a gap, not a guess.

```
Win           how the game ends. In the list, one card away, or missing.
Setup         what has to happen first (the bend, the lock, the board gate)
Mana          analyze_mana_base: grade, the color that is short
Interaction   can we live to that turn (the count from analyze_deck)
See cards     draw, tutors, goldfish keep rate — do we find the win
```

Add one row when the win needs it: tokens (`find_tokens`), a creature type, a graveyard, a board gate. Skip the row when the win does not need it.

A plan that names a win and leaves a surrounding piece blank is not ready to ask.

## How to talk

One question per turn. Wait.

Two plans. The one you recommend is first. Each plan is the upgrade, in five lines: **Target** (`B__ · EDHcheck Power __–__/10`), **Goal**, **Win**, **Turn**, **Budget**. Plain words. Name the pattern you would cut ("the Rat lords"). Do not print the new 99.
- **Deterministic EDHcheck Power Score math:** Because Tutors (`18%`) + Explicit Spellbook Combos (`15%`) + WotC Game Changers (`15%`) = `48%` of EDHcheck's 0–10 Power Score, always show the exact predicted EDHcheck Power Score on each plan (e.g. **Plan 1: `B3 · Power 7.5–8.5/10`** with `2–3` explicit Spellbook combos + `6+` budget tutors + `2–3` budget Game Changers vs. **Plan 2: `B2 · Power ~4.8–5.2/10 ceiling`** for a zero-combo/zero-tutor fair build).

A plan you already know cannot be bought at the cap gets `Budget: does not fit` on that plan, with the dollar gap. Offer the cheaper win next to it. Do not hide the expensive one.

"Just upgrade it" or a message that already names the win and the budget is a yes. Print the locked card in that reply, then build.

## Hand back (first turn)

Lead with the question. Then what this list is doing. Then the fit table. Then the plans.

```
Question: Which plan — 1 or 2? Cap is about $__, unless you name another.

This list: <one sentence — the plan it actually has>

Win:           ...
Setup:         ...
Mana:          ...
Interaction:   ...
See cards:     ...

1. <name>  (recommended)
   Goal:    Every game we ...
   Win:     The game ends when ...
   Turn:    turn __
   Budget:  fits at $__ | does not fit (needs about $__, cap is $__)

2. ...
```

## After they pick

```
Locked
Goal:     ...
Win:      ...
Turn:     ...
Budget:   $__
Keep:     pasted cards that still do a job
Cut:      the pattern that fights the plan
Together: setup, mana, interaction, and seeing cards — one line each

Build this? Say yes, or say what to change.
```

A change updates the lock and asks again.

## Build

Same win as the paste: `get_skill("nero-tune")` and follow its **Build** section.

A different win: `get_skill("nero-build")`. Paste the locked block into that skill. Cards from the paste that do a locked job stay. Say which pasted cards left, and which job they failed.

## After the list

`price_decklist(budget_target=<their cap>)` on the new list. The first line is one of these, before any card name:

- **Fits.** Total is at or under the cap, and the locked win is still in the list.
- **Tight.** Under the cap only because of cuts the tool named. Say those cuts.
- **Does not fit.** Over the cap, or the win was dropped to get under it. Use the block below and stop. The list under it is a draft. Do not tell them to buy it.

```
Budget:  does not fit
Need:    about $__ to keep <the win>
Cap:     $__
Short:   $__
Drop:    <the piece> — the win then becomes <the cheaper win>
Or:      raise the cap to $__
```

## Example

User pastes a $180 Vren list of Rat lords and says nothing about money.

`nero-tune` read: Vren is a removal deck that makes Rats. The lords are the trap. Price is about $180, so the cap is $180.

```
Question: Which plan — 1 or 2? Cap is about $180, unless you name another.

This list: Rat lords. Vren wants edicts. The Rats show up after something dies.

1. Edict pile  (recommended)
   Goal:    Every game we remove their creatures, and the Rats are the result.
   Win:     The game ends under a pile of edicts, not a lord buff.
   Turn:    the turns we are casting removal
   Budget:  fits at $180

2. Keep the lords, add a combo
   Budget:  does not fit if the combo piece is the expensive one — name the gap from get_card before they pick.
```

Stop. The new list starts when they say yes.
