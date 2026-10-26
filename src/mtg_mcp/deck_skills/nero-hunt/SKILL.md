---
name: nero-hunt
description: >
  Find ~$100 Bracket 4 cards that do two jobs: draw, ramp, and
  interaction first, then a counter, removal spell, or draw spell that
  is also the plan. Use after nero-read and nero-lines. Cuts the
  4-mana enabler that does nothing the turn you cast it.
---

# Find cards that do two jobs

Jobs and the win shape come from `nero-read`. The win comes from `nero-lines`. If either block is missing, load that skill first.

If `search_cards` or `get_card` is missing, say so and stop.

Draw, ramp, and interaction are in the list before a card that is only the theme. Counts sit higher than a normal video list. The best card dies to one cheap answer, so the answer and the redraw have to be in the deck. The win does not matter if the deck cannot play up to that turn.

## Where to look

1. `reference_cards` with `color_identity`, the role, `max_mana_value=3`, `min_decks=3`, `sort="decks"`. Proven cards. If that tool is missing, say so and use `search_cards` only.
2. `search_cards` for the card that pool will miss. `order="usd"` or `order="cmc"`, not `edhrec`. Every query has `f:commander` and `id<=` the commander's colors. Cap `usd<5` unless the user raised the budget. The cap is the deck at about $100, not a hard per-card cap.

Replace COLOR and WORD.

- Counter that cares about the plan: `id<=COLOR o:counter o:spell (o:flying OR o:WORD) mv<=2 usd<3 f:commander`
- Removal that is the plan: `id<=COLOR (o:destroy OR o:exile OR o:sacrifices) o:WORD mv<=3 usd<3 f:commander`
- Draw off an action the deck already takes: `id<=COLOR o:draw o:WORD mv<=3 usd<4 f:commander`
- Ramp: `id<=COLOR otag:ramp mv<=2 usd<3 f:commander`
- Type doubler, and the deck is not that type: `get_card` the commander and the combo piece, read the subtype, then `id<=COLOR t:WORD (o:additional OR o:twice OR o:double) usd<5 f:commander`

## Cut test

`get_card` before a card is a candidate (pass `include_forge_tags=True` on key synergy candidates to verify `deck_has`, `deck_needs`, and `sacrifice_costs` AST nodes). `get_card_rulings` if the line depends on a trigger happening twice.

- Blank the turn it enters, and you need a lap around the table to use it: out. Mondrak, Glory Dominus is the picture. `{2}{W}{W}`, and tokens you create later are doubled. The turn you cast it, nothing happens. EDHREC puts it in token decks. Out even when the price on `get_card` fits the budget.
- Theme only: wait. It is not a veggie.
- Two jobs: it jumps the list.
- Colored pips the mana base or the commander's discount cannot pay: out. `{U}{U}` is a real cost in three or four colors. Rowan's discount does not touch colored mana.

`edhrec_recommendations` with `budget="budget"` and the decklist comes after candidates exist, and only to see the shell. Do not lead with those cards.

## Pictures

Confirm both with `get_card`. Do not skip it because this file names them.

- A deck that already wants fliers: Lofty Denial over Counterspell. `{1}{U}`. Tax `{1}`, or `{4}` if you control a flyer. One blue pip.
- The deck is not Wizards. The commander and a combo piece are. Naban, Dean of Iteration. Kefka, Court Mage and Dualcaster Mage are Wizards. Dualcaster's enter trigger copies a spell and you may change the target, so it can point a counter back at the counter on Kefka. Naban's ruling: a Wizard's own enter trigger happens an additional time, and each instance chooses its own targets. The original spell still resolves. Kefka's own enter trigger is doubled the same way. Naban is interaction and the plan. He is not wizard tribal.

## Hand back

```
Veggies:  draw __ / ramp __ / interaction __   (in the list before theme-only cards)
Keep:     Card — job + job — the query
Cut:      Card — blank this turn, or theme only, or pips you cannot pay
Shell:    one EDHREC card you saw and rejected
```

Five keeps. Further hits stay in notes until a keep is cut.

## Example

A three-color flying deck. Run the counter query with `o:flying`. Lofty Denial passes: it counters, and the deck already has the flyer. Counterspell is the comparison, not the default: `{U}{U}`, and it does not care that you have fliers.
