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

1. Run `analyze_mana_base` and read `grade` (`S` down to `D-`), `recommended_land_count` (Karsten's 99-card regression `31.42 + 3.13 * avg_cmc - 0.75 * ramp * 0.28`), `tipping_point`, `speed_breakdown` (`untapped` / `conditional` / `tapped`), and `color_requirements` (exact hypergeometric 90% source requirements per color, with `+2` turns of grace for reactive Instants). Also check `color_pips` and `land_color_sources` from `analyze_deck`.
2. Write `sources_have / sources_needed (deficit)` and pips per land source for each of the commander's colors. Any color with `deficit > 0` or the highest pip-to-source ratio is the short color.
3. Land-count thumb comes from `reference_principles(source="nero")` rules of thumb alongside `analyze_mana_base.recommended_land_count`. If `reference_principles` is missing, read `src/mtg_mcp/data/library/nero/source.json`. Say which one you used. A 2-mana dork commander can sit near 30 lands. A 4-mana commander can sit at 34. A landfall commander can sit near 39. Do not add a land just because the count is under 38.
4. Name the taplands from `analyze_mana_base.land_groups` (`speed == "tapped"`). He wants few or none. Utility lands and MDFCs count as both a land and a spell. `get_card` before you call a land tapped.
5. One swap: cut a tapland, or a land of a surplus color, for an untapped or conditional source of the short color. Candidates come from `search_lands(color_identity=..., cycle=..., max_price=5.0)` and `reference_cards(role="land", color_identity=..., min_decks=3)` (or `get_library().search_cards` with `PYTHONPATH=src`). Then `get_card`. Budget fixing he actually uses: pain lands (`cycle="pain"`), fast lands (`cycle="fast"`), bond lands (`cycle="bond"`), pathways (`cycle="pathway"`), verges (`cycle="verge"`), snarls (`cycle="reveal"`), horizon lands (`cycle="canopy"`), filter lands (`cycle="filter"`), Exotic Orchard, Command Tower.
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
