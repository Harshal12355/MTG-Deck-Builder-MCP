---
name: defcat-turn
description: >
  Rescore a card as a free spell on an opponent's turn: an
  enters-the-battlefield answer, flash, or a card you would rather
  hold. Use after defcat-read, or when a list is only scored for your
  own main phase. Cuts the card that is blank until your next turn.
---

# What if this is free on their turn

For a comparison commander, the shell and the bar come from `defcat-read`, and the fuel from `defcat-fuel`. Load those first. For any other deck, start at the cut test.

If `search_cards` or `get_card` is missing, say so and stop.

A hit wants mana value 1–3. A fuel spell sets a high bar, and a cheap card clears it more often. Score the card for the moment it resolves. That moment may be an opponent's turn, and it may be before the spell that triggered the ability.

You may decline the free cast. Interaction with nothing on the stack goes to hand. Interaction lives in the hand. Payoffs live in the library.

## Where to look

`f:commander` and `id<=` the commander's colors. `order="cmc"`.

- Enters and answers something: `id<=COLOR o:enters (o:destroy OR o:exile OR o:"return target") mv<=3 f:commander`
- Already has flash: `id<=COLOR keyword:flash mv<=3 f:commander`
- Gives your spells flash: `id<=COLOR (o:"have flash" OR o:"as though they had flash") f:commander`
- Better after combat: `id<=COLOR o:"untapped creatures" f:commander`

`get_card` before a card is a candidate. `get_card_rulings` on the commander if the free cast ignores timing. Rashmi does: type-based timing is ignored, and other restrictions still apply.

## Cut test

- Blank until your next turn: out. A creature with summoning sickness is the picture, unless the shell is "it arrives on their turn and swings on yours."
- You would rather cast it in the second main, after your attackers have tapped: say so. Destroying untapped creatures is that card.
- Mana value high, and it is not fuel: out.
- An X spell as a hit: out. X in the library is 0.

## Pictures

Confirm with `get_card`.

Leyline of Anticipation: you may cast spells as though they had flash. One card that moves the deck onto other turns. A deck of cards that already have flash is the same job. It is not required for the shell.

## Hand back

```
Hits:    Card — mana value — what it does on their turn — the query
Hold:    Card — interaction you keep when the stack is empty
Flash:   already on the card | a card that grants it | not needed
Cut:     Card — blank until your turn, or an X spell you wanted to reveal
```

Five hits. Cards from a second shell stay in notes.
