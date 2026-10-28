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
get_card(commander, include_forge_tags=True)
    |
    v
get_card_rulings          if the ability uses X, "this turn", or a timing word
engine converter check    cost, normal-action fuel, payoff (cards / mana / outlet)
five bend questions       scope, lock, fuel, board gate, leftover cost
synergy multipliers       double-duty hooks, A+B twins, parity-breaking stax
win shape                 one spell, a pile of the same effect, or overlapping combos
3-4 jobs                  a later card that does none of them is out
```

1. `get_card(commander, include_forge_tags=True)` on the commander. Quote the ability that is not the creature type, and inspect `forge_tags` (`deck_has`, `deck_needs`, `abilities`, `triggers`, `sacrifice_costs`) for explicit synergy hooks.
2. `get_card_rulings` when the sequence matters. Rowan is this case. Skip the call only when the text has no timing, no X, and no "this turn".
3. Run **NeRo's 3-Question Engine Check (Converter, Not Billboard)**. Do not build the creature type or keyword label (`Vren` is not Rat tribal, it converts `Removal -> Rat Army`; `Meria` converts `0-mana artifacts -> Mana + Impulse Draw`; `Hapatra` converts `-1/-1 removal -> Deathtouch Snakes -> Draw/Sac Loops`; `Tannuk` converts `2nd Land -> Draw + Burn Outlet`):
   - **Cost & speed:** Does it cost `2–4 MV` (or immediately draw/impact the board the turn it enters, like `Kefka`)? If it costs `5+ MV` and must survive a turn cycle, name how the deck bridges that gap (rituals, dorks, or reanimation).
   - **Fuel (normal game action):** Does it reward an action you *already want to take* with $0.25 commons (playing lands, killing creatures, discarding dead cards, casting cheap spells), or trap you into 25 bad theme cards?
   - **Payoff (Cards, Mana/Bodies, or Combo Outlet):** Which of the three engine outputs does the commander supply in the command zone? Whatever it lacks must be supplied by the 99.
4. Answer five bend questions from the tool result:
   - Scope. The next spell, or every spell this turn? One trigger, or each end step?
   - Lock. When is the number fixed? Life you lose after that moment does not count.
   - Fuel. What has to happen before the lock? Name the amount, not "some life".
   - Board gate. What permanent, power total, or fodder must already be on the battlefield before the commander's ability turns on (`Station 2+ / 8+`, `Saddle`, `Crew`, sacrifice a creature/land)? When a board gate exists, early ramp and draw slots must provide that body or permanent type (e.g. a 2-power ramp creature over `Farseek` so it both ramps and stations `Hearthhull` the turn it arrives).
   - Leftover cost. Generic mana only, or the colored pips too? Pips you still pay are part of the bend.
5. Name the trap. It is the card or EDHREC theme shell the surface suggests that pays off on the wrong turn, costs $20+ because of tribal demand, or gives 1 when the plan needs 3 or 4. `get_card` it before you call it a trap.
6. Name the **~$100 synergy multipliers & anti-clunk checks** that make the engine punch above its price without bricking draws:
   - **Natural Bracket Fit (B4 Hair-Trigger vs. B3 Freight Train):** Is the commander a natural Bracket 4 1-card/2-card infinite (`Celes, Rune Knight` + Persist, `Stella Lee` + untap cantrip, `The Jolly Balloon Man` + untap dork, `Rowan`, `Zirda`, `Kinnan`, `Malcolm`)? If building for Bracket 3, name the **Domino / Fulcrum Engine** that triggers the commander 3–5 times a turn without off-theme clunk (`Sister Hospitaller` -> `Metamorphosis Fanatic` -> `Phyrexian Delver` -> `Alesha` on Celes; `Viridian Revel` + `Inspiring Statuary` on `Vraska, the Silencer`).
   - **25th-Percentile Card Floor & Unconditional Draw (Salubrious Snail + Card-Forge AST rule):** Before your engine is online, cards must work on an empty board. Verify Card-Forge `ValidCard$` / `Cost$` types: never pair creature-sacrifice draw (`Village Rites`, `Corrupted Conviction`, `Midnight Reaper`) with a commander that makes non-creature artifacts (`Vraska, the Silencer`'s Treasures) or lacks free fodder. At least `9+` of your `12–15` draw slots must be **unconditional / self-starting** (`Night's Whisper`, `Ripples of Undeath`, `Black Market Connections`, `Dark Confidant`, `Mystic Remora`, `Talion`), and situational/6+ MV bricks must stay `<= 5`.
   - **Double-duty & Fulcrum slots:** Which cards bridge setup and payoff here (`Skeleton Key` = evasion + loot in `Hapatra`; `Bridgeworks Battle` = land + removal; `Essence Flux` = protection + ETB re-trigger)?
   - **Parity-breaking stax & low curve (`~2.0–2.6` avg MV):** Which stax/tax piece does the commander naturally sidestep (`Winter Orb` with `Meria`; rule-of-law with `Ratadrabik`'s activated abilities; `Dauthi Voidwalker` in black)?
7. Write the win shape in one sentence. Do not add cards in this skill.

A win does not have to be a combo.

- One spell. Rowan: a black/red finisher cast after the discount is locked. The video uses Torment of Hailfire. `get_card` it. Her discount does not remove the two black pips.
- A pile of the same effect. Vren, the Relentless: opponents' creatures that would die are exiled, and each end step makes that many Rats. The pile is edicts. The Rats are the result of removal.

## Hand back

```
Surface:  what the obvious EDHREC billboard theme is
Engine:   <Normal action> -> <Commander converter> -> <Cards / Mana / Bodies / Outlet>
Bend:     the rule, the lock, the mana you still pay
Trap:     one card, and the turn it actually does something
Fuel:     what happens before the ability, and how much
Synergy:  double-duty hook + A/B twin density + stax parity the commander breaks
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
