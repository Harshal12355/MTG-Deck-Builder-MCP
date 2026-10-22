---
name: nero-mana
description: >
  Fix a Commander mana base the NeRo way from analyze_deck color pips versus
  land sources. Use when the user asks for a mana-base pass, color screw,
  taplands, pip counts, or a tune left one color's pips well above its sources.
---

# Mana base the NeRo way

Land count follows the commander's mana value and the plan. The Command Zone's 38 is the wrong ruler. The tool does not flag a cutoff. Do not invent one.

If `analyze_deck` is not in this session, say so and stop.

## Order

```
analyze_deck
    |
    v
color_pips  vs  land_color_sources     one line per color
reference principles, land thumb        his range, from the tool or source.json
get_card on every land you swap         enters untapped? identity? Commander legal?
```

1. Read `color_pips` and `land_color_sources` from `analyze_deck`. Sources are lands only (`produced_mana`). A ramp spell is not a source. A fetch that puts a land into play is not a source.
2. Write pips per source for each of the commander's colors. The highest ratio is the short color. A color outside the identity (a splash land that taps for anything) is not a short color.
3. Land-count thumb comes from `reference_principles(source="nero")` rules of thumb. If that tool is missing, read `src/mtg_mcp/data/library/nero/source.json`. Say which one you used. A 2-mana dork commander can sit near 30 lands. A 4-mana commander can sit at 34. A landfall commander can sit near 39. Do not add a land just because the count is under 38.
4. Name the taplands. He wants few or none. Utility lands and MDFCs count as both a land and a spell. `get_card` before you call a land tapped.
5. One swap: cut a tapland, or a spell that does not make the short color, for an untapped source of the short color. Candidates come from `reference_cards(role="land", color_identity=..., min_decks=3)` or, if that tool is missing, `get_library().search_cards` in this repo (`PYTHONPATH=src`). Then `get_card`. Budget fixing he actually uses: pain lands, fast lands, snarls, horizon lands, filter lands, Exotic Orchard, Command Tower.
6. Stop after that swap plus at most four more, each tied to a pip count. Do not rebuild the mana base.

## Hand back

```
Pips/sources:  G 35/19 (1.8)   B 32/17 (1.9)   R 12/14 (0.9)
Short:         B, then G
Lands:         34 (commander costs 4, so this count stays)
Taplands:      the ones get_card confirmed
Change:        cut X → add Y, because <which color is short>
```

## Example

Auntie Ool costs {1}{B}{R}{G}. Report G 35/19, B 32/17, R 12/14. Black and green are short. Red is fine. 34 lands stays. Do not add a 35th land to chase a template.
