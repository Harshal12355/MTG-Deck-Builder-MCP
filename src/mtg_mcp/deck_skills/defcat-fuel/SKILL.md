---
name: defcat-fuel
description: >
  Find spells whose printed mana value stays high while the mana you
  pay stays low: delve, pitch, evoke, convoke, affinity. Use after
  defcat-read, or when cascade or a top-of-library commander needs
  fuel. The free card has to cost less than that printed value.
---

# Cast a high mana value for a little mana

The bar comes from `defcat-read`. If that block is missing, load it first. If it says `Bar: none`, write `Fuel: none` and stop.

If `search_cards` or `get_card` is missing, say so and stop.

Mana value is what is printed. Delve, a pitch cost, evoke, convoke, improvise, and affinity change what you pay. They do not change the printed mana value. That gap is the fuel.

A cheap interaction spell is not fuel. It sets a low bar, so the top card usually goes to hand. That replaces the card. It does not cast it for free.

The free cast cannot choose an alternate cost. A pitch spell or an evoke spell is fuel when you cast it by paying that cost. You do not get the same cost again when it is the card on top. `get_card_rulings` on the commander when that difference is why the card is in the deck.

## Where to look

`f:commander` and `id<=` the commander's colors on every query. `order="usd"` or `order="cmc"`.

- Delve: `keyword:delve id<=COLOR f:commander`
- Pitch: `o:"rather than pay" id<=COLOR f:commander`
- Evoke: `keyword:evoke id<=COLOR f:commander`
- Convoke, improvise, affinity: `keyword:convoke`, `keyword:improvise`, `o:affinity`, with the same colors and `f:commander`

`get_card` before a card is a candidate. Read the printed mana value and the mana you actually pay. If those two numbers are close, it is not fuel.

## Cut test

- Printed mana value 1–3: that is a hit, not fuel. It belongs in `defcat-turn`.
- You needed the alternate cost on the free cast too: out. The free cast does not get it.
- Nothing happens the turn you cast it, and it is not raising the bar for a hit you named: out.

## Pictures

Confirm both with `get_card`. Do not skip it because this file names them.

- Treasure Cruise is `{7}{U}`, mana value 8, delve. Pay `{U}` and exile seven cards. The bar is 8.
- Commandeer is `{5}{U}{U}`, mana value 7. Exile two blue cards rather than pay that cost. The bar is 7. When Commandeer is the revealed card, the pitch is not available.

## Hand back

```
Fuel:   Card — printed MV, mana you pay — the query
Bar:    the mana value that cast sets
Not:    Card — the two numbers are close, or the cheap cost dies on a free cast
Draw:   one cheap spell that puts the top card in hand instead of casting it
```

Five fuel cards. Further hits stay in notes.
