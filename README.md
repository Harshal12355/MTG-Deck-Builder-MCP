# mtg-deckbuilder-mcp

[![tests](https://github.com/Harshal12355/MTG-Deck-Builder-MCP/actions/workflows/tests.yml/badge.svg)](https://github.com/Harshal12355/MTG-Deck-Builder-MCP/actions/workflows/tests.yml)

An MCP server (`mtg-deckbuilder`) that lets Cursor, Claude Desktop, Claude Code, or any MCP client build, tune, goldfish, and publish Magic: The Gathering decks with live card data instead of LLM memory.

```text
┌───────────────────┬───────────────────────┬──────────────┬───────────────┬───────────────────┐
│     Scryfall      │  Commander Spellbook  │    EDHREC    │   Archidekt   │ Reference Library │
│ Cards • Rulings   │  In-Deck & 1-Card-    │ High-Synergy │ Public Decks  │ NeRo's 28 Tested  │
│ Printings • Price │  Away Combo Lines     │ & Top Cards  │ & Meta Share  │ ~$100 B4 Lists    │
└─────────┬─────────┴───────────┬───────────┴──────┬───────┴───────┬───────┴─────────┬─────────┘
          └─────────────────────┴──────────────────┼───────────────┴─────────────────┘
                                                   ▼
                               ┌───────────────────────────────────────┐
                               │     mtg-deckbuilder MCP (23 Tools)    │
                               │  + 16 Deckbuilding Skills & Prompts   │
                               │  + Monte Carlo Goldfish Simulator     │
                               └───────────────────┬───────────────────┘
                                                   ▼
       ┌─────────────────────────┬─────────────────┴───────┬─────────────────────────┐
       ▼                         ▼                         ▼                         ▼
┌──────────────┐          ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│ 1. NeRo      │          │ 2. Defcat    │          │ 3. Based 33  │          │ 4. Moxfield  │
│ • Commander  │          │ • Turn phase │          │ • 33-card    │          │ • Bulk-paste │
│   bend & win │          │   (1st/2nd / │          │   1-game core│          │   #tags list │
│ • Veggies +  │          │   their turn)│          │ • Sim 33 1st │          │ • Copy-paste │
│   2-job cards│          │ • MV bar &   │          │ • Scale 3x33 │          │   Markdown   │
│ • Pips/lands │          │   cheap fuel │          │ • Split 3x33 │          │   primer     │
└──────────────┘          └──────────────┘          └──────────────┘          └──────────────┘
```

## Highlights

- **Scryfall**: full Scryfall syntax search, fuzzy card lookup, official Gatherer rulings, cheapest printings, and daily USD prices.
- **Universal Decklist Parser**: accepts pastes from Moxfield (including printings, foils, `#tags`, and trailing commander blocks), MTG Arena, Archidekt (`[Category]` tags), MTGO, Deckstats (`*CMDR*`), or plain `1 Card Name` lines. Secret Lair and Universes Beyond alternate names (e.g. *Black Panther's Redirection*, *Thrum of the Vestige*) resolve automatically to their oracle card.
- **Deck Analysis & Custom Templates**: checks format legality (deck size, singleton/copy limits, colour identity, banlist), mana curve, colour pips vs. land sources, heuristic card roles (ramp, draw, removal, counterspells, wipes, tutors, protection, recursion), WotC Game Changers, total USD price, and fit against The Command Zone's template (or custom category targets).
- **Monte Carlo Goldfish Simulator (`simulate_deck`)**: shuffles and plays out up to 50,000 games with multiplayer Commander free-mulligan rules, untapped/tapped land sequencing, mana dorks (with summoning sickness), mana rocks, rituals, land ramp, and tutors standing in for missing combo pieces.
- **Commander Spellbook**: finds combos already in your deck, combos you are one card away from, and searches the full Spellbook database.
- **EDHREC & Archidekt**: fetches high-synergy and top cards by theme or budget (filtering out cards already in your list), searches public Archidekt decks by commander/card/owner/bracket, pulls full categorized decklists, and tallies card inclusion % across top-viewed decks.
- **Reference Library & Moxfield Importer**: ships with 28 tested ~$100 high-power Bracket 4 / budget cEDH decks from [NeRo (`@_NeRo`)](https://moxfield.com/users/_NeRo), complete with author role tags, capture-time prices, distilled principles, mulligan guides, and win lines. Import or refresh any Moxfield builder with `moxfield_import_user`.
- **16 Built-in Deckbuilding Skills (`get_skill` & MCP Prompts)**: encodes a complete three-school deckbuilding pass (**NeRo / Budget Bros** + **Defcat** + **Based Deck Department 33-Card**) plus automated **Moxfield `#tag` + Primer** generation.

---

## MCP Tools (23 Tools)

### Cards & Scryfall

| Tool | What it does |
|---|---|
| `search_cards` | Scryfall search (`query`, `order`, `direction`, `limit`, `detail`), e.g. `id<=bg o:"sacrifice" t:creature usd<3 f:commander` |
| `get_card` | One card by (fuzzy or exact) name and optional `set_code`, with oracle text, legalities, USD price, and heuristic deck roles |
| `get_card_rulings` | Official Gatherer/Scryfall rulings for a card, plus oracle text for context |
| `get_card_printings` | All printings of a card sorted cheapest USD first, with set code, collector number, and foil prices |
| `autocomplete_card_name` | Up to 20 real card name suggestions for a partial or misspelled name |
| `random_card` | Random card, optionally restricted by a Scryfall query (e.g. `is:commander id:ur`) |

### Deck Analysis, Pricing, Principles & Goldfish Simulation

| Tool | What it does |
|---|---|
| `analyze_deck` | Full deck report: format legality, mana curve, average nonland MV, colour pips vs. land sources, heuristic roles, template comparison, Game Changers, and USD price |
| `price_decklist` | Quick price check of a decklist: per-card and total USD price sorted most expensive first, plus unpriced cards |
| `deckbuilding_template` | The Command Zone's Commander template (38 lands, 10 ramp, 12 card advantage, 12 targeted disruption, 6 mass disruption, 30 plan), custom overrides, overlap calculation, and colour-scoped Scryfall queries |
| `deckbuilding_principles` | Budget Pub Stomper & Budget Bros MTG principles for ~$100 high-power Bracket 4 builds: engine commander, win line first, build backwards from ideal turn, average MV ~2.0, 29–34 lands, veggies before theme, and cutting blank-this-turn enablers |
| `simulate_deck` | Goldfish a deck 100–50,000 times (`turns`, `trials`, `on_play`, `extra_cards_per_turn`, `seed`): reports 7-card keep rate, commander cast rate by turn, and assembly rate by turn for each win line (`[["Card A", "Card B | Card C"]]`) |

### Combos (Commander Spellbook)

| Tool | What it does |
|---|---|
| `find_combos` | Combos already in a decklist and combos one card away, with step-by-step execution instructions |
| `search_combos` | Search Commander Spellbook combos by query, e.g. `card:"Thassa's Oracle"`, `result:"infinite mana" id<=bg`, `cards=2` |

### EDHREC & Archidekt

| Tool | What it does |
|---|---|
| `edhrec_recommendations` | EDHREC recommendations for a commander (and optional `partner`), filtered by `theme`, `budget` (`any`/`budget`/`expensive`), or `categories`; pass `decklist` to exclude cards already in the deck |
| `edhrec_card` | EDHREC profile for a single card: top commanders that play it and high-synergy pairings |
| `archidekt_search_decks` | Search public Archidekt decks by `commander`, `card`, `name`, `owner`, `format`, `colors`, `exact_colors`, `bracket` (1–5), and `order` (`views`, `newest`, `updated`, `name`) |
| `archidekt_get_deck` | Fetch one public Archidekt deck by ID or URL: commanders, builder category counts, cards by category, approximate price, and a ready-to-use `decklist` string |
| `archidekt_popular_cards` | Sample 1–30 top Archidekt decks for a commander (optionally filtered by `bracket`) and compute card inclusion % and most common builder category; pass `decklist` to see only new cards |

### Reference Library & Skills

| Tool | What it does |
|---|---|
| `reference_library` | Overview of all reference builders and every deck in the library with archetype, land count, average MV, win-line count, and capture-time price |
| `reference_principles` | Distilled deckbuilding principles and rules of thumb from the reference builders' primers, with evidence decks |
| `reference_cards` | Proven cards from the reference library ranked by deck count, price, or MV; filter by `role`, `color_identity`, `min_decks`, `max_price`, `max_mana_value`, `query`, or `theme` |
| `reference_card` | How a single card is used across the reference library: decks playing it, roles tagged by the builder, commander usage, and decks `considering` it |
| `reference_deck` | Full reference deck entry by commander, name, or Moxfield ID: plan, ideal turn, mulligan guide, `win_lines` (ready for `simulate_deck`), key cards, stats, and full `decklist` |
| `reference_compare` | Compare a decklist against the reference library to surface proven staples in its colour identity that it isn't running yet, grouped by role |
| `moxfield_import_user` | Import or refresh every public Commander deck (cards, author tags, card metadata, and raw Markdown primers) of a Moxfield user into the reference library |
| `get_skill` | Load one of the 16 deckbuilding skills from `src/mtg_mcp/deck_skills/` (also exposed as MCP prompts via `prompts/list` and `prompts/get`) |

---

## Deckbuilding Skills & The Three-School Pass

Every build or tune runs **three deckbuilding schools on the same list** via `get_skill` (or MCP prompts):

1. **NeRo / Budget Bros School**: finds the rule the commander bends past its surface EDHREC theme, locks the win condition first (one spell, an edict/effect pile, or overlapping 2–4 card combos where every piece works alone), fills draw/ramp/interaction ("veggies") at higher-than-usual counts, and demands that utility cards do two jobs the turn they are cast.
2. **Defcat School**: evaluates *when* in the turn each card wants to resolve (first main, second main, or an opponent's turn), checks whether casting one card makes another card better, and—when the commander sets a mana-value bar (e.g. Rashmi, cascade, top-of-library)—pairs cheap alternate-cost high-MV fuel (delve, pitch, evoke, convoke, affinity) with 1–3 MV flash/ETB hits.
3. **Based 33-Card School (Based Deck Department / Brother Frog)**: since an average Commander game sees ~1/3 of the deck (33 cards), builds and goldfishes a tight **33-card 1-game deck first** (`based-core` + `simulate_deck` at low variance), then replicates each slot two more times (`based-scale`, `33 × 3 = 99`) so the deck is a reliable "silly goose" instead of a once-a-year "pigeon"—or deals an existing 99 into three 33-card piles (`based-split`) to expose uneven role splits, `1/0/0` orphans (`Archmage Emeritus`), and slow random value engines (`Exalted Flamer of Tzeentch`).

```text
New Commander ("Build a $100 Rowan")           Existing Decklist / Link ("Tune my Vren list")
                │                                                      │
                ▼                                                      ▼
   1. deckbuilding_principles                             1. nero-tune (load decklist text)
   2. nero-build + reference_deck check                   2. reference_principles(source="nero")
   3. nero-read  ──► Surface vs. Bend, Trap, Jobs         3. analyze_deck + price_decklist
   4. defcat-read ─► Turn window & MV Bar (or "none")     4. get_card(commander) + defcat-read
   5. nero-lines ──► 1 spell / pile / overlapping combos  5. reference_deck + based-split (3 x 33)
   6. based-core ──► Lock 33-card 1-game slot budget      6. find_combos + reference_compare
   7. nero-hunt + defcat-turn (+ defcat-fuel if Bar)      7. nero-hunt + defcat-turn (for new adds)
   8. nero-goldfish on 33-card core (test at low var)     8. nero-goldfish (33 Pile A + 99 before/after)
   9. based-scale ─► Triplicate 33 x 3 = 99 (0 orphans)   9. nero-mana (if a colour is short)
  10. nero-mana  ──► Colour pips vs. land sources        10. moxfield-primer (on request)
  11. analyze_deck + price_decklist + find_combos
  12. nero-goldfish on 99 (compare vs. 33-card seed)
  13. edhrec_recommendations + archidekt_popular_cards
  14. moxfield-primer (#tags + Markdown primer)
```

### All 16 Skills (`src/mtg_mcp/deck_skills/`)

| Skill | School | When to use |
|---|---|---|
| `nero-build` | NeRo + Defcat + Based | Master build order for a new commander at ~$100 high-power Bracket 4 |
| `nero-tune` | NeRo + Defcat + Based | Evaluate and tune an existing decklist: one plan-fixing swap first, then at most four more tied to tool numbers |
| `nero-read` | NeRo | Read a commander past its EDHREC theme: what locks, what mana you still pay, the trap card, win shape, and 3–4 jobs |
| `nero-lines` | NeRo | Pick the win: one finisher spell, a pile of the same effect, or overlapping 2–4 card combos with no dead pieces |
| `nero-hunt` | NeRo | Find ~$100 Bracket 4 veggies and double-duty cards; cut 4-mana enablers that do nothing the turn they enter |
| `nero-mana` | NeRo | Fix colour pips vs. land sources and cut taplands using land counts matched to commander MV and plan |
| `nero-goldfish` | NeRo | Run `simulate_deck` (on both the 33-card core and the full 99) to test 7-card keep rate, commander cast turn, and win-line assembly |
| `defcat-build` | Defcat | Second-school pass inside `nero-build`: turn timing, mana-value bar check, and fuel/hit separation |
| `defcat-read` | Defcat | Read commanders that compare mana value, reveal the top card, or trigger on the first spell each turn |
| `defcat-turn` | Defcat | Rescore cards for the moment they resolve (1st main, 2nd main, or free on an opponent's turn) |
| `defcat-fuel` | Defcat | Find high printed-MV spells that cost little mana to pay (delve, pitch, evoke, convoke, affinity) when a bar exists |
| `based-build` | Based 33-Card | Third-school pass inside `nero-build` and `nero-tune`: 33-card 1-game core first, `33 × 3 = 99` scaling, and `3 × 33` split audits |
| `based-core` | Based 33-Card | Draft and goldfish a 33-card 1-game Commander deck (`1/3` of 99) at low variance before choosing 66 more cards |
| `based-scale` | Based 33-Card | Replicate a tested 33-card core two more times (`33 × 3 = 99`) with functional twins and zero `1/0/0` orphans |
| `based-split` | Based 33-Card | Split an existing 99-card deck into three 33-card piles to expose uneven splits, `1/0/0` orphans (`Archmage Emeritus`), and fake job slots (`Exalted Flamer of Tzeentch`) |
| `moxfield-primer` | Publishing | Tag every card in the final list (`#ramp`, `#draw`, `#combo`, `#land`...) for Moxfield bulk paste and generate a full Markdown primer |

---

## Reference Library

`src/mtg_mcp/data/library/<source>/` stores real, tested decklists with the builder's own card tags, capture-time card metadata, and primer notes (plan, ideal turn, mulligan guide, win lines, key cards).

- **Bundled source**: [NeRo (`@_NeRo` on Moxfield)](https://moxfield.com/users/_NeRo) — 28 decks (mostly ~$100 high-power Bracket 4 / budget cEDH), captured `2026-10-20`.
- **Canonical roles** (`ROLES`): `ramp`, `draw`, `tutor`, `counter`, `removal`, `wipe`, `protection`, `stax`, `combo`, `recursion`, `untap`, `clone`, `tokens`, `evasion`, `land`.
- **Browsable Markdown docs**: [`docs/library/`](docs/library/README.md) contains human- and agent-readable [principles](docs/library/nero/PRINCIPLES.md), the full [card library by role](docs/library/nero/CARD_LIBRARY.md), and [every deck's plan and win lines](docs/library/nero/DECKS.md).
- **Add or refresh a Moxfield builder**: call `moxfield_import_user(username="...")` (hand-written deck notes are preserved), then regenerate the Markdown docs:
  ```bash
  python scripts/build_library_docs.py
  ```
- **Custom library path**: set `MTG_MCP_LIBRARY_DIR=/path/to/library` to store or load the library outside `src/mtg_mcp/data/library/`.
- **Price note**: library prices are capture-time snapshots for the exact printings in the builder's list. Always re-check live prices with `price_decklist` and cheapest copies with `get_card_printings`.

---

## Deckbuilding Template

For standard Commander builds, `deckbuilding_template` and `analyze_deck` check lists against The Command Zone's template:

| Category | Default | What counts |
|---|---|---|
| `lands` | 38 | Land cards |
| `ramp` | 10 | Mana rocks and dorks, land fetch, Treasure makers, extra land drops |
| `card_advantage` | 12 | Draw and impulse-draw sources |
| `targeted_disruption` | 12 | Spot removal, counterspells, bounce, edicts, fights |
| `mass_disruption` | 6 | Board wipes and sweepers |
| `plan` | 30 | Cards advancing the deck's strategy (any nonland card not matching the above) |

The targets sum to **108 for 99 slots**, meaning ~9 cards should fill two roles. Any category target can be overridden per call by passing `template={"lands": 34, "ramp": 12}` to `deckbuilding_template` or `analyze_deck`.

---

## Install & Client Setup

Requires **Python 3.10+**.

```bash
cd mtg-deckbuilder-mcp
pip install -e .          # or: uv pip install -e .
mtg-mcp --help
```

### Cursor IDE

This repo includes [`.cursor/mcp.json`](.cursor/mcp.json) and workspace rules in `.cursor/rules/` (`use-mtg-mcp.mdc`, `full-deck-pass.mdc`, `ponytail.mdc`).

To run against the hosted server (default in `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "mtg-deckbuilder": {
      "url": "https://mcp.swag31415.com/mcp"
    }
  }
}
```

Or to run locally via stdio in `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "mtg-deckbuilder": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/MTG-Deck-Builder-MCP", "run", "mtg-mcp"]
    }
  }
}
```

### Claude Desktop

Open **Settings → Developer → Edit Config** and add:

```json
{
  "mcpServers": {
    "mtg-deckbuilder": {
      "command": "mtg-mcp"
    }
  }
}
```

If `mtg-mcp` is not on the `PATH` Claude Desktop sees, use the full binary path (`which mtg-mcp`) or `uv`:

```json
{
  "mcpServers": {
    "mtg-deckbuilder": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/MTG-Deck-Builder-MCP", "run", "mtg-mcp"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add mtg-deckbuilder -- mtg-mcp
```

### Streamable HTTP Server

```bash
mtg-mcp --http --host 0.0.0.0 --port 8000   # serves streamable HTTP at http://0.0.0.0:8000/mcp
```

When running behind a reverse proxy or tunnel (Cloudflare, nginx, Tailscale), the MCP SDK rejects non-localhost `Host` headers by default. Pass `--allowed-host` twice per hostname (`name:*` for `host:port` and bare `name` for default port 443):

```bash
mtg-mcp --http --host 0.0.0.0 --port 8000 --allowed-host mtg.internal:* --allowed-host mtg.internal
```

### Docker

The `Dockerfile` runs `mtg-mcp` as an unprivileged user (`nobody`). With no arguments it runs over stdio; pass `--http` flags to expose port `8000`:

```bash
docker build -t mtg-mcp .
docker run --rm mtg-mcp --help
```

**Stdio (Claude Desktop / Cursor without local Python):**

```json
"mtg-deckbuilder": {
  "command": "docker",
  "args": ["run", "-i", "--rm", "mtg-mcp"]
}
```

**Streamable HTTP (`http://localhost:8000/mcp`):**

```bash
docker run --rm -p 8000:8000 mtg-mcp --http --host 0.0.0.0 --port 8000 --allowed-host mtg.internal:* --allowed-host mtg.internal
```

*(Note: because the container runs as `nobody`, mount a writable directory and set `-e MTG_MCP_LIBRARY_DIR=/data/library` if you want to run `moxfield_import_user` inside Docker.)*

---

## Example Prompts

- *"Build me a $100 Rowan, Scion of War Bracket 4 deck with a Moxfield primer and tagged decklist."*
- *"Tune this deck the NeRo way:"* + paste a Moxfield export or Archidekt URL.
- *"What combos am I one card away from in this list?"*
- *"Simulate this deck 10,000 times with `seed=42` and compare the turn-3 commander cast rate before and after cutting 2 taplands for pain lands."*
- *"Find the 15 most viewed Archidekt decks for Atraxa in Bracket 3 and show which cards most of them run that I don't."*
- *"What are NeRo's most-played Dimir interaction and ramp staples under $3?"*

---

## Tests

The test suite (`tests/test_all.py`) is 100% offline using deterministic API fakes (`tests/fakes.py`):

```bash
python -m unittest discover -s tests -v
```

---

## Notes, Caching & Rate Limits

| Upstream Source | Min Request Interval | Cache TTL | Notes |
|---|---|---|---|
| **Scryfall** (`api.scryfall.com`) | `100 ms` | `1–24 h` | Uses `/cards/collection` in batches of 75 cards. Prices are daily TCGplayer USD market prices for the returned printing. |
| **Commander Spellbook** (`backend.commanderspellbook.com`) | `250 ms` | `6–12 h` | Official combo search and deck combo detection API. |
| **EDHREC** (`json.edhrec.com`) | `500 ms` | `24 h` | Unofficial JSON endpoints loaded by EDHREC's web pages. Best-effort; may change if EDHREC updates its frontend. |
| **Archidekt** (`archidekt.com`) | `1.0 s` | `6 h` | Unofficial JSON endpoints for public deck search and deck pages. `archidekt_popular_cards` fetches 1 request per sampled deck (~15s for 15 decks). |
| **Moxfield** (`api2.moxfield.com`) | `1.0 s` | — | Unofficial API used by `moxfield_import_user` (~2 requests per deck). Often blocked by Cloudflare on datacenter IPs; paste decklists directly when blocked. |

- **Role tagging** in `analysis.py` is a regex heuristic over oracle text—great for spotting structural gaps, always verified with `get_card` during the skill pass.
- **Fan Content Policy**: follows Wizards of the Coast's Fan Content Policy and Scryfall's API terms. Keep projects built on this free and do not imply official endorsement.

---

## Roadmap

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the upcoming 10-phase plan:

1. **Part 1 (Phases 1–5 — Foundation & Moxfield Loop)**: `captured_at` provenance on library tools, one-call `moxfield_get_deck`, deterministic `tag_decklist`, persistent SQLite HTTP cache (`~/.cache/mtg-mcp/http_cache.sqlite3`), and golden-deck CI regression evals.
2. **Part 2 (Phase 6 — Speed & Richer Reports)**: per-card cache inside `Scryfall.collection()`, parallel host calls via `asyncio.gather`, automatic WotC Bracket 1–5 estimation in `analyze_deck`, and EUR + cheapest-printing budget swap finder in `price_decklist`.
3. **Part 3 (Phases 7–10 — EDHcheck Tool Suite)**: `analyze_mana_base` (exact `math.comb` hypergeometric on-curve cast rates & land cycle classification), `search_lands`, color-aware goldfish + custom `mulligan_targets`, `compare_decks` (A/B deck diff), `check_pod` (4-deck Rule 0 pod checker), and `find_tokens`.

---

## Repository Layout

```text
src/mtg_mcp/
  __init__.py         package version
  server.py           FastMCP server, 23 MCP tools, CLI entry point (--http / stdio)
  http.py             per-host rate-limited, retrying async HTTP client + in-memory TTLCache
  scryfall.py         Scryfall API client (search, named, collection batches, rulings, printings)
  decklist.py         multi-format decklist parser (Moxfield, Arena, Archidekt, MTGO, plain text)
  analysis.py         legality, mana curve, pips vs. sources, role heuristics, template report
  goldfish.py         Monte Carlo goldfish simulator (mulligans, mana sources, rituals, tutors, win lines)
  principles.py       Budget Pub Stomper & Budget Bros MTG ~$100 Bracket 4 deckbuilding principles
  skills.py           SKILL.md frontmatter parser, get_skill loader, and MCP prompt registration
  spellbook.py        Commander Spellbook API client (find_my_combos, search)
  edhrec.py           EDHREC client (commander recommendations, themes, budget, single-card stats)
  archidekt.py        Archidekt client (deck search, full deck summary, popular cards across top decks)
  library.py          reference library loader, role normalizer, card/deck search, staple comparison
  moxfield.py         Moxfield user importer for reference library sources
  deck_skills/        16 deckbuilding skills (nero-*, defcat-*, based-*, moxfield-primer)
  data/library/       bundled reference library data (nero/source.json, decks.json, cards.json)
scripts/
  build_library_docs.py   regenerate docs/library/ Markdown files from src/mtg_mcp/data/library/
docs/
  ROADMAP.md          10-phase architecture, performance, and EDHcheck tool suite roadmap
  library/            browsable Markdown reference library (PRINCIPLES.md, CARD_LIBRARY.md, DECKS.md)
.cursor/
  mcp.json            Cursor MCP server config
  rules/              Cursor workspace rules (full-deck-pass.mdc, use-mtg-mcp.mdc, ponytail.mdc)
  skills/             Ponytail engineering workflow skills
tests/
  fakes.py            deterministic offline HTTP fakes for Scryfall, Spellbook, EDHREC, Archidekt, Moxfield
  test_all.py         offline unit and integration test suite
```
