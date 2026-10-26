# Architecture — mtg-deckbuilder-mcp

This document is the source of truth for how code is organized and how new features land. It follows patterns from the [MCP reference servers](https://github.com/modelcontextprotocol/servers) (thin transport, grouped tools), [GitHub MCP](https://github.com/github/github-mcp-server) (domain-split `pkg/`), and [Supabase MCP](https://github.com/supabase-community/supabase-mcp) (platform clients + feature modules).

## Layers

```text
MCP host (Cursor, Claude, HTTP)
              │
              ▼
┌─────────────────────────────────────────┐
│  server.py + tools/*     TRANSPORT       │  Args → JSON, no business rules
│  wiring.py               HTTP + resolve  │
└─────────────────┬───────────────────────┘
                  │
    ┌─────────────┼─────────────┬──────────────┐
    ▼             ▼             ▼              ▼
 analysis/*   goldfish.py   library.py   decklist.py
 (deck math)  (simulate)    (reference)  (parse)
                  │
                  ▼
         scryfall.py helpers + clients/* + http.py
```

**Allowed imports**

| From | May import |
|------|------------|
| `tools/*`, `server.py` | `wiring`, `analysis`, `goldfish`, `library`, clients |
| `analysis/*` | `decklist`, `scryfall` helpers (`oracle_text`, …), sibling `analysis` modules |
| `goldfish.py` | `analysis.roles.card_roles`, `decklist` |
| `clients/*` | `http.py` only |
| `analysis/*` | Must **not** import `server`, `tools`, or MCP |

**Card data:** Scryfall-shaped `dict[str, Any]` keyed by lowercased name. **Deck data:** `ParsedDeck` from `decklist.py`.

## Directory layout (target)

```text
src/mtg_mcp/
  server.py              # FastMCP instance, short INSTRUCTIONS, CLI main()
  wiring.py              # Shared HttpClient, _resolve_deck(), set_http_client()
  tools/
    __init__.py          # register_tools(mcp)
    cards.py             # search_cards, get_card, …
    deck.py              # analyze_deck, simulate_deck, mana, price, compare, pod, tokens, template, principles
    combos.py
    edhrec_tools.py
    archidekt_tools.py
    reference.py
    skills_tool.py       # get_skill

  analysis/
    __init__.py          # Stable public re-exports (see below)
    _card_utils.py       # COLORS, _pips, _front_lower
    roles.py             # card_roles, role regexes
    template.py          # TEMPLATE_*, resolve_template, template report
    bracket.py           # bracket, power, school scores, combo tiers
    mana.py              # LAND_CYCLES, analyze_mana, classify_land
    compare.py           # compare_decks_analysis
    pod.py               # evaluate_pod
    tokens.py            # collect_deck_tokens
    legality.py          # copy limits, color identity checks
    core.py              # analyze() orchestrator (until fully slimmed)

  decklist.py, goldfish.py, library.py, principles.py, skills.py
  scryfall.py, spellbook.py, edhrec.py, archidekt.py, moxfield.py, forge.py, http.py
  deck_skills/           # Canonical agent SOPs (mirror to .cursor/skills/)
```

## Stable public API (`from mtg_mcp.analysis import …`)

These names must keep working for tests, `server.py`, and `goldfish.py`:

- `analyze`, `card_roles`, `analyze_mana`, `compare_decks_analysis`, `evaluate_pod`, `collect_deck_tokens`
- `resolve_template`, `template_overlap`, `TEMPLATE_CATEGORIES`, `LAND_CYCLES`

## MCP tool groups

| Module | Tools | Shared setup |
|--------|-------|--------------|
| `cards.py` | `search_cards`, `get_card`, rulings, printings, autocomplete, `random_card` | `_clients().scryfall` |
| `deck.py` | `analyze_deck`, `simulate_deck`, `analyze_mana_base`, `search_lands`, `price_decklist`, `compare_decks`, `check_pod`, `find_tokens`, `deckbuilding_template`, `deckbuilding_principles` | `wiring.resolve_deck` |
| `combos.py` | `find_combos`, `search_combos` | deck + Spellbook |
| `reference.py` | `reference_*`, `moxfield_import_user` | `library.py` |

Server `INSTRUCTIONS` stay a **tool index**; full deck pass lives in `deck_skills/` and `.cursor/rules/`.

## Testing contract

1. `python3 -m unittest discover -s tests -v` before and after every structural PR.
2. `tests/test_regression.py` + `tests/fixtures/golden_atraxa_pipeline.json` — golden pipeline; update fixture only on intentional behavior change.
3. `SkillChainTests` — `get_skill("…")` references and packaged ↔ Cursor skill file parity.

## Migration checklist

Status key: `[x]` done, `[ ]` planned.

### Foundation

- [x] Golden pipeline + skill-chain regression tests (`tests/test_regression.py`)
- [x] `AGENTS.md` + this document
- [x] Remove stray `ai-instructions/` (non-MTG content)
- [x] `wiring.py` — shared HTTP and deck resolution out of `server.py`
- [x] `analysis/` package (`analysis/core.py` + stable `analysis/__init__.py` re-exports)
- [x] `tools/__init__.py` scaffold + `register_tools(mcp)` hook on server startup

### analysis/ split (one PR per step, tests green)

- [x] `_card_utils.py` + `roles.py`
- [x] `mana.py` (`LAND_CYCLES`, `analyze_mana`, `classify_land`)
- [x] `template.py`
- [x] `legality.py`
- [x] `bracket.py` (sets, `_score_and_bracket`, synergy)
- [x] `compare.py`, `pod.py`, `tokens.py`
- [x] `analyze.py` orchestrator (removed monolithic `core.py`)

### tools/ split

- [x] `tools/cards.py`, `deck.py`, `combos.py`, `edhrec_tools.py`, `archidekt_tools.py`, `reference.py`, `skills_tool.py`
- [x] `register_tools(mcp)` + `server.py` ~130 lines (re-exports tools for tests)

### Optional later

- [ ] Hosted toolsets (subset of tools over HTTP, GitHub-style)
- [ ] Split `tests/test_all.py` by domain
- [ ] MCP Python SDK v2 migration (`MCPServer` / `ToolError`)

## Adding a new tool

1. Implement logic in the right **domain** module (or client).
2. Add a **thin** `@mcp.tool` handler in the appropriate `tools/*.py` file.
3. Register in `tools/__init__.py` if using split registration.
4. Add or extend offline test in `tests/` (fake HTTP via `wiring.set_http_client`).
5. Mention the tool in server `INSTRUCTIONS` one line; update a skill only if agents must call it in a pass.

## Skills

- Edit only `src/mtg_mcp/deck_skills/<name>/SKILL.md`.
- Copy to `.cursor/skills/<name>/SKILL.md` (or run CI sync when added).
- Regression test fails if copies diverge.
