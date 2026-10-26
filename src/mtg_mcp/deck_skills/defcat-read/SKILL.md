---
name: defcat-read
description: >
  Read a commander that compares mana value, reveals the top card, or
  triggers on the first spell each turn, before any other card is named.
  Use for Rashmi, cascade, reverse control, or "how am I building this."
  Also the questions to ask of any commander: when in the turn, and
  whether two cards help each other.
---

# Read the comparison, not the theme

Defcat's picture is Rashmi, Eternities Crafter. The lesson is the comparison. Creature type, enchantments, and a pile of big creatures are shells someone picks later.

If `get_card` is not in this session, say so and stop. Do not recite oracle text from memory.

## Order

```
get_card(commander, include_forge_tags=True)
    |
    v
get_card_rulings     X, "each turn", "without paying", "rather than pay"
four questions
one shell            a sentence, not a card
3 jobs
```

1. `get_card(commander, include_forge_tags=True)` the commander. Quote the ability that looks at a mana value, a top card, or the first spell of a turn, and check `forge_tags` (`triggers`, `abilities`, `deck_needs`) if present.
2. `get_card_rulings` when that ability uses X, "each turn", "without paying", or an alternate cost. Skip only when the text has none of those.
3. Answer from the tool result:
   - Window. Your turn only, or the first spell of every turn? Opponents' turns are extra casts.
   - Bar. What does the spell you just cast set, and what must the next card be under it?
   - Miss. A land, an equal mana value, a card you decline. Where does it go?
   - Free cast. Alternate costs you cannot choose. Additional costs you still pay. X on the stack versus X on a card in the library.
4. Name the trap. It is the shell the surface theme suggests. `get_card` a card before you call it the trap. An X spell you reveal is a bad hit: in the library X is 0, and a free cast must choose 0. An X spell you cast for a large X is fuel, because the stack uses the chosen X.
5. Write the shell in one sentence. Enchantments that keep working. Creatures that can act the turn they arrive. One type. A second shell is a different deck. Do not add cards in this skill.

## No comparison

The ability does not compare mana value, reveal the top card, or trigger on the first spell of a turn. Write `Bar: none`. Shell is the win shape from `nero-read`. Answer "Any commander" and stop. Do not invent fuel.

## Any commander

Ask these even when the commander is not Rashmi.

- When in the turn does this card want to resolve? Your first main, your second main after attackers tap, or an opponent's turn?
- If it is free because something else was cast, does it still do the job?
- Are these two cards competing for a slot, or does casting one make the other better?

## Hand back

```
When:     first main | second main | their turn
Window:   your turn | every turn | n/a
Bar:      none | what the cast spell sets, and what the next card needs
Miss:     where a card goes when you do not cast it | n/a
Free:     alternate costs, additional costs, X | n/a
Trap:     one card or one shell, and why it fails the bar
Shell:    one sentence
Jobs:     from nero-read when Bar is none, otherwise
          1 cast high printed value for little mana
          2 a cheaper card that is good on an opponent's turn
          3 cheap interaction in hand, so the payoffs stay in the library
```

Stop after that block. Fuel is `defcat-fuel`. Hits are `defcat-turn`.

## Example

User: "Read Rashmi, Eternities Crafter."

`get_card`: whenever you cast your first spell each turn, reveal the top card. You may cast it without paying its mana cost if it is a spell with lesser mana value. If you don't, put it into your hand.

`get_card_rulings`: the trigger is not only on your turn. A land goes to hand. The free spell resolves before the spell that triggered it. You cannot choose an alternate cost on that free cast. You still pay mandatory additional costs. X on the stack uses the chosen value. X in the library is 0, and a free cast must choose 0.

```
Window:   every turn (first spell)
Bar:      printed mana value of the spell you cast; the top card must be lesser
Miss:     hand (lands always)
Free:     no alternate cost; additional costs still paid; revealed X is 0
Trap:     an X spell you wanted to reveal — the free cast chooses 0
Shell:    one sentence the user picks
Jobs:     1 fuel  2 a hit on their turn  3 interaction in hand
```
