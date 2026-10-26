# Agent guide — mtg-deckbuilder-mcp

## Layout

- **Domain logic:** `src/mtg_mcp/analysis.py`, `goldfish.py`, `decklist.py`, clients (`scryfall.py`, …)
- **MCP surface:** `src/mtg_mcp/server.py` — thin tools; no new business logic here
- **Deckbuilding SOPs:** `src/mtg_mcp/deck_skills/` (canonical). `.cursor/skills/<name>/` must stay identical
- **Tests:** `tests/` — offline fakes only (`tests/fakes.py`)

## Test-driven refactors

1. Run the full suite before changing structure:
   ```bash
   python3 -m unittest discover -s tests -v
   ```
2. **Golden pipeline** (`tests/test_regression.py` + `tests/fixtures/golden_atraxa_pipeline.json`) locks parse → analyze → combos → simulate (`seed=1`) → mana → tokens → compare on the fake Atraxa deck. If a refactor changes numbers, fix the bug or **intentionally** update the fixture in the same PR with a short note in the commit message.
3. **Skill chain** tests scan `get_skill("…")` references in deck skills, `.cursor/skills`, and `.cursor/rules` and fail on typos or drift between packaged vs Cursor skill copies.
4. Prefer adding a focused assertion to an existing test class over a one-off script. Split modules under `src/mtg_mcp/` only when golden + `test_all.py` stay green.

## What not to use

- `ai-instructions/` is leftover from another project (Django/shipping). Ignore it for MTG MCP work.

## CI

GitHub Actions runs `python -m unittest discover -s tests` on Python 3.10 and 3.12 after `pip install -e .`.
