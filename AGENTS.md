# Agent guide — mtg-deckbuilder-mcp

Read **`docs/architecture.md`** for layers, module map, migration checklist, and how to add tools.

## Layout (short)

| Layer | Location |
|-------|----------|
| MCP transport | `server.py`, `tools/` (split in progress) |
| HTTP + deck resolve | `wiring.py` |
| Deck math | `analysis/` (`core.py` today → split into roles, mana, bracket, …) |
| Simulation | `goldfish.py` |
| Parse | `decklist.py` |
| Upstream APIs | `scryfall.py`, `spellbook.py`, `edhrec.py`, `archidekt.py`, `moxfield.py`, `http.py` |
| Reference data | `library.py`, `data/library/` |
| Agent SOPs | `deck_skills/` only — mirror to `.cursor/skills/` |

**Import rule:** domain code never imports `server` or MCP. Tools call domain; domain uses card dicts + `ParsedDeck`.

## Test-driven refactors

```bash
python3 -m unittest discover -s tests -v
```

- **Golden pipeline:** `tests/test_regression.py` + `tests/fixtures/golden_atraxa_pipeline.json`
- **Skill chain:** `get_skill("…")` references + packaged vs Cursor `SKILL.md` parity
- One structural change per PR; tests green before merge. Update golden JSON only when behavior intentionally changes.

## Skills

Edit `src/mtg_mcp/deck_skills/<name>/SKILL.md`, then copy to `.cursor/skills/<name>/SKILL.md`.

## CI

GitHub Actions: Python 3.10 and 3.12, `pip install -e .`, full `tests/` suite.
