---
name: nero-tune
description: >
  Tune an existing Commander deck against NeRo's principles with the
  mtg-deckbuilder MCP: one plan-fixing swap, then at most four more,
  each tied to a tool number. Use when the user pastes a deck, shares a
  Moxfield, Archidekt, or MTGO link, or asks to tune, cut, upgrade, or
  check a list, including NeRo, _NeRo, budget cEDH, or Bracket 4.
---

# Tune a deck the NeRo way

NeRo (@_NeRo) builds ~$100 high-power Bracket 4. A swap is a 1-for-1 quality bump that still does the deck's jobs. Ten better cards beat one bomb. A staple he plays is a candidate, not an automatic add.

If `reference_principles` is not in this session, say so and stop. Do not invent the report.

Get the list as text first. Moxfield has no public API. For an Archidekt URL, `archidekt_get_deck` and use its `decklist`. For one of his decks, `reference_deck` and use its `decklist`.

## Order

```
list as text
    |
    v
reference_principles(source="nero")     the test
analyze_deck + price_decklist           the picture
get_card(commander)                     the bend, in one sentence
reference_deck(commander)               his plan, if he built this commander
find_combos                             in the deck, then one card away
reference_compare(min_decks=3)          his staples this list skips
simulate_deck                           only if win lines are known
get_card on every swap                  oracle, identity, Commander legal
```

1. `reference_principles(source="nero")`. Grade against the tool result. Do not recite principles from memory.
2. `analyze_deck` on the full list. Pass `commanders` if the list does not mark them. `price_decklist` for the real total. The ~$100 cap is the deck, not a per-card cap.
3. `get_card` on the commander. One sentence: the rule it breaks. If the list is built around the surface theme (Rat tribal for Vren, landfall tokens for Tannuk), that is the first cut.
4. `reference_deck` for this commander. Use his plan, mulligan, and `notes.win_lines` as the comparison, not as cards to copy blindly.
5. `find_combos`. Say what is already in the deck, then what is one card away. Prefer the one-card-away line whose new piece is good alone.
6. `reference_compare` with the decklist, `min_decks=3`. Raise `min_decks` for only his real staples. Set `max_price` when the user names a budget. Check each candidate against the deck's jobs.
7. `simulate_deck` when you have win lines (his notes, or lines you just confirmed). Compare versions. It is not a win rate.
8. `get_card` before you name any add or cut. `get_card_rulings` if the line depends on timing.

`edhrec_recommendations` comes after the scorecard, with the decklist passed in, and only to show the cookie-cutter shell this deck should not become. Do not lead with those adds. Do not fill a gap the report does not show.

## Hand back

```
Bend:        <one sentence — does this list actually do that?>
Price:       $__   (~$100, or the user's cap)
Avg MV:      __    (thumb from the tool)
Lands:       __ / curve says __
Interaction: __    (thumb from the tool, if this is a control shell)
Tutors:      __
Lines:       in the deck / one card away / pieces that are dead alone
Curve:       commander cast by the ideal turn, in %   (or "not simulated")

Change:      cut X → add Y, because <one number or one combo>
Then:        at most four more, each tied to a number
```

Lead with the one swap that fixes the plan. A card he plays in three or more decks still has to pass the jobs test.

## Example

User pastes a Vren list full of Rat lords.

Bend from `get_card`: Vren is a removal deck that makes Rats. `analyze_deck` shows the removal count. The first swap cuts a lord for a cheap edict. `reference_compare` may offer more edicts. Name one. Do not add a tutor package: his Vren runs zero tutors on purpose.
