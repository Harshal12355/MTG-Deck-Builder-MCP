---
name: deck-plan
description: >
  Plan a Commander deck with the user before any decklist: one goal,
  one way the game ends, in plain words, then hand off to nero-build.
  Use when the user names a commander with no list, or asks to plan,
  brew, discuss a plan, pick a strategy, or decide how the deck wins.
---

# Plan the deck before the list

A plan is one sentence you can say at the table: we do this, and the game ends when that happens. Cards come after that sentence is locked.

If `get_card` or `get_skill` is missing, say so and stop. Do not invent the commander's text or a win.

Default, unless the user already said otherwise: about $100, Bracket 4. Say that assumption once. Do not ask budget, bracket, and plan in the same turn. The plan is the question.

## Order

```
commander (or archetype request)
    |
    v
reference_principles(source="nero")     how ~$100 engines beat $1,000 staples
get_card(commander, include_forge_tags=True)
reference_deck(commander)               his list, if he already built it
get_skill nero-read                     engine converter, bend, trap, synergy hooks, jobs
get_skill defcat-read                   when, bar or "none"
get_skill nero-lines                    real wins, still no decklist
    |
    v
2 or 3 plans, one question, stop
    |
    +-- user picks --> locked card, one question: build?
    |
    +-- user says yes --> get_skill nero-build
```

0. **If the user has not picked a commander yet** (e.g. asks for a theme like reanimation, landfall, stax, spellslinger): check `reference_library` and `search_cards`, verify every candidate with `get_card`, and rank 3–5 commanders using **NeRo's 3-Question Engine Check**:
   - **Cost:** Comes down early (`2–4 MV`) or immediately draws/impacts on entry (`Kefka`).
   - **Fuel:** Rewards a normal game action you already want to take with cheap cards (playing lands, killing creatures, discarding dead cards, casting cheap spells) instead of forcing 25 bad theme cards.
   - **Payoff:** Converts that normal action into **Cards**, **Mana/Bodies**, or a **Combo/Win Outlet** in the command zone (combines steps of the archetype's bucket brigade).
1. `reference_principles(source="nero")` and `get_card(commander, include_forge_tags=True)`. One sentence: what the card does on the turn you cast it, and what it converts (`Normal Action -> Commander -> Free Resource / Win`). Quote the ability that is not the creature type.
2. `reference_deck`. A hit is plan 1. Use his goal and his `notes.win_lines`. Say the deck name. Do not hide his list behind a new brew.
3. `get_skill("nero-read")`, then `get_skill("defcat-read")`. You need Engine Converter, Bend, Trap, Synergy Multipliers (double-duty slots, A+B twins / density over tutors, parity-breaking stax), Jobs, When, and Bar. `Bar: none` is a complete answer.
4. `get_skill("nero-lines")`. This finds the real ways the game can end. It is not permission to print a 99. Keep two or three win shapes. A one-spell or pile win does not grow a combo package.
5. Show the picture (including why the engine works on ~$100) and the plans. Ask one question. Stop. Do not call `nero-build`, `nero-hunt`, or `based-core` in this turn.

## How to talk

One question per turn. Wait for the answer.

At most three plans. Put the one you recommend first. Each plan is four lines: Goal, Win, Turn, Not this. Plain words. No card dump. A plan may name the finisher or the effect (`Torment of Hailfire`, "a pile of edicts"). It does not name a mana base.

A bare commander is not a yes. "Just build it", "don't ask", or a message that already names the win is a yes to build. Still print the locked card in that same reply, then `get_skill("nero-build")`.

If they already named the win, skip the menu. Show the locked card and the trap you are not building. Ask only when a tool result contradicts what they asked for.

## The picture

Draw one game and the ~$100 engine converter. Five beats, one line each.

```
Setup      what has to happen before the commander matters
Commander  the turn it comes down, and what it starts
Engine     <normal game action> -> <commander converter> -> <free cards / mana / bodies>
Synergy    how ~$100 beats $1,000 here (double-duty cards, A+B twins/density, low ~2.0 MV + 1-mana shields, stax parity)
Win        the turn we want, and how the game ends
```

## Hand back (first turn)

Lead with the question. Then the picture. Then the plans.

```
Question: Which plan — 1, 2, or 3?

Setup:      ...
Commander:  ...
Engine:     ...
Synergy:    ...
Win:        ...

1. <name>  (recommended)
   Goal:     Every game we ...
   Win:      The game ends when ...
   Turn:     turn __
   Not this: the obvious theme, and the turn it actually does something

2. ...
3. ...

Assuming: ~$100, Bracket 4, unless you say otherwise.
```

Two plans is enough when a third would be the trap. Do not invent a third to fill the slot.

## After they pick

Restate the lock. One question. Stop.

```
Locked
Goal:     ...
Win:      ...
Turn:     ...
Not this: ...
Jobs:     1 …  2 …  3 …  4 …

Build the 99 from this plan? Say yes, or say what to change.
```

A change updates the lock and asks again. Do not build on a half-yes.

## Build

`get_skill("nero-build")` and follow it. Paste the locked block into that skill's hand-back. `nero-lines` fills this win. It does not shop for another. If a tool result cannot do the locked win, stop and say so.

## Example

User: "Plan a deck for Rowan, Scion of War."

`get_card`, `nero-read`, `defcat-read`, `nero-lines`. Bar is none. Win shape is one spell. No combo package.

```
Question: Which plan — 1 or 2?

Setup:      lose 3 or 4 life, with mana open
Commander:  turn 3 or 4, tap, generic mana on black and red spells drops
Engine:     cast a hand of black and red spells that turn
Win:        one big black finisher ends it

1. Discount into one finisher  (recommended)
   Goal:     Every game we buy a turn where our black and red spells are cheap.
   Win:      The game ends when one finisher (Torment of Hailfire) resolves after the tap.
   Turn:     the turn we tap Rowan
   Not this: a life-loss theme. Phyrexian Arena pays 1 life on the wrong turn.

2. Storm the discount
   Goal:     Every game we cast a lot of cheap black and red spells the turn we tap.
   Win:      The game ends when those spells add up, not one big X.
   Turn:     the turn we tap Rowan
   Not this: a combo package. The win is the pile of spells, and the pieces have to be good alone.

Assuming: ~$100, Bracket 4.
```

Stop. The list starts when they say yes.
