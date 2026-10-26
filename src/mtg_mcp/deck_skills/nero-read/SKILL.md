---
name: nero-read
description: >
  Read a commander past its EDHREC theme before any card is named:
  what locks, what you still pay, the trap card, the win shape, and
  3-4 jobs. Use when building a ~$100 Bracket 4 deck and no list exists
  yet, or when a list is built around the obvious theme.
---

# Read the commander past the theme

Budget Bros builds ~$100 lists for a greedy high-power Bracket 4 table. The first mistake is building the theme EDHREC shows.

If `get_card` is not in this session, say so and stop. Do not recite oracle text from memory.

## Order

```
get_card(commander)
    |
    v
get_card_rulings          if the ability uses X, "this turn", or a timing word
four questions
win shape                 one spell, a pile of the same effect, or overlapping combos
3-4 jobs                  a later card that does none of them is out
```

1. `get_card` the commander. Quote the ability that is not the creature type.
2. `get_card_rulings` when the sequence matters. Rowan is this case. Skip the call only when the text has no timing, no X, and no "this turn".
3. Answer five questions from the tool result:
   - Scope. The next spell, or every spell this turn? One trigger, or each end step?
   - Lock. When is the number fixed? Life you lose after that moment does not count.
   - Fuel. What has to happen before the lock? Name the amount, not "some life".
   - Board gate. What permanent, power total, or fodder must already be on the battlefield before the commander's ability turns on (`Station 2+ / 8+`, `Saddle`, `Crew`, sacrifice a creature/land)? When a board gate exists, early ramp and draw slots must provide that body or permanent type (e.g. a 2-power ramp creature over `Farseek` so it both ramps and stations `Hearthhull` the turn it arrives).
   - Leftover cost. Generic mana only, or the colored pips too? Pips you still pay are part of the bend.
4. Name the trap. It is the card the surface theme suggests that pays off on the wrong turn, or for 1 when the plan needs 3 or 4. `get_card` it before you call it a trap.
5. Write the win shape in one sentence. Do not add cards in this skill.

A win does not have to be a combo.

- One spell. Rowan: a black/red finisher cast after the discount is locked. The video uses Torment of Hailfire. `get_card` it. Her discount does not remove the two black pips.
- A pile of the same effect. Vren, the Relentless: opponents' creatures that would die are exiled, and each end step makes that many Rats. The pile is edicts. The Rats are the result of removal.

## Hand back

```
Surface:  what the obvious theme is
Bend:     the rule, the lock, the mana you still pay
Trap:     one card, and the turn it actually does something
Fuel:     what happens before the ability, and how much
Win:      one spell | a pile | overlapping combos
Jobs:     1 …  2 …  3 …  4 …
```

Stop after that block. Card search is `nero-hunt`. Combo search is `nero-lines`.

## Example

User: "Read Rowan, Scion of War."

`get_card`: menace, and tap to discount black and/or red spells you cast this turn by life lost this turn. Activate only as a sorcery. `get_card_rulings`: X is set once, when the ability resolves, and only generic mana is reduced.

```
Surface:  big X spells
Bend:     every black/red spell this turn, generic only, X locks on resolution, sorcery speed
Trap:     Phyrexian Arena — 1 life at the next upkeep, so it counts and it is not the turn
Fuel:     lose 3 or 4 life before you activate
Win:      one spell (Torment of Hailfire), after the lock
Jobs:     1 lose life before the tap  2 cast a hand of spells after it
          3 one of those spells ends the game  4 interaction that is black or red
```

Big Score is `{3}{R}` and makes two Treasures. At 3 life lost before the tap it costs `{R}`. Confirm with `get_card` before it goes in a list.
