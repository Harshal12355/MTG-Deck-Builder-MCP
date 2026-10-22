# mtg-deckbuilder-mcp

[![tests](https://github.com/Harshal12355/MTG-Deck-Builder-MCP/actions/workflows/tests.yml/badge.svg)](https://github.com/Harshal12355/MTG-Deck-Builder-MCP/actions/workflows/tests.yml)

An MCP server that lets Claude (or any MCP client) help build and tune Magic: The Gathering decks with real data instead of memory:

- **Scryfall**: card search with full Scryfall syntax, card lookup, rulings, printings, prices
- **Decklists**: paste a list from Moxfield, Arena, Archidekt, MTGO or plain text
  (alternate printing names such as *Black Panther's Redirection* or *Thrum of the Vestige* are resolved to the real card)
- **Deck analysis**: legality, mana curve, colour pips vs land sources, card roles (ramp / draw / removal / wipes / tutors…), fit against the deckbuilding template, Game Changers, price
- **Deckbuilding template**: Commander decks are built and checked against The Command Zone's template, and the player can change any of its numbers (see below)
- **Commander Spellbook**: combos already in your deck, and combos one card away
- **EDHREC**: high-synergy and top cards for a commander, by theme or budget, skipping cards you already run
- **Archidekt**: search public decks by commander, card, owner, colours or bracket, pull any deck's full list, and tally what the most-viewed decks for a commander actually run

## Tools

| Tool | What it does |
|---|---|
| `search_cards` | Scryfall search, e.g. `id<=bg o:"sacrifice" t:creature usd<3 f:commander` |
| `get_card` | One card by (fuzzy) name, with oracle text, legalities, price and deck roles |
| `get_card_rulings` | Official rulings for a card |
| `get_card_printings` | All printings, cheapest first |
| `autocomplete_card_name` | Real card names for a partial/misspelled name |
| `random_card` | Random card, optionally filtered |
| `analyze_deck` | Full deck report (see above) |
| `price_decklist` | Per-card and total USD price |
| `deckbuilding_template` | The Commander template to build to, with optional custom numbers and colour-limited Scryfall searches per category |
| `deckbuilding_principles` | Principles for focused, powerful budget decks: engine commander, win line first, build backwards, average mana value ~2.0, synergy over staples, 29-34 lands, interaction that protects the win. Also a step-by-step build process (Budget Bros MTG): analyze the commander, win condition first, more ramp/draw/interaction than usual, synergy in every slot, no cookie-cutter lists, untapped budget duals |
| `simulate_deck` | Goldfish a deck thousands of times: keep rate, chance to cast the commander by each turn, and chance each win line is assembled by each turn |
| `find_combos` | Combos in the deck / one card away (Commander Spellbook) |
| `search_combos` | Search Commander Spellbook, e.g. `card:"Thassa's Oracle"` |
| `edhrec_recommendations` | EDHREC suggestions for a commander; pass `decklist` to get only *new* cards |
| `edhrec_card` | EDHREC data for a single card |
| `archidekt_search_decks` | Search public Archidekt decks by commander, card, title, owner, format, colours or bracket |
| `archidekt_get_deck` | One Archidekt deck by id or URL: commanders, category counts, cards by category, price, and a `decklist` for the other tools |
| `archidekt_popular_cards` | Sample the top Archidekt decks for a commander and report each card's inclusion %; pass `decklist` to see only new cards |
| `reference_library` | Overview of the reference library: builders and every deck with archetype, lands, average MV and price |
| `reference_principles` | The reference builders' principles, distilled from their primers, with evidence decks |
| `reference_cards` | Proven card choices ranked by how many reference decks play them; filter by role, colour identity, price, mana value, theme |
| `reference_card` | How one card is used across the reference decks (roles, decks, decks considering it) |
| `reference_deck` | One reference deck: plan, mulligan guide, win lines (ready for `simulate_deck`), key cards, stats and full `decklist` |
| `reference_compare` | Proven staples in a deck's colour identity that it doesn't play yet, grouped by role |
| `moxfield_import_user` | Import or refresh every public Commander deck (cards, author tags, primers) of a Moxfield user as a library source |

## Reference library

`src/mtg_mcp/data/library/<source>/` holds real, tested decklists from builders worth learning from, with the
builder's own card tags, card metadata at capture time, and hand-written notes distilled from their primers
(plan, ideal turn, mulligan guide, win lines, key cards). The first source is
[NeRo](https://moxfield.com/users/_NeRo): 28 decks, mostly ~$100 high-power Bracket 4 / budget cEDH, captured 2026-10-20.

Readable versions for browsing (and for agents without the MCP): [`docs/library/`](docs/library/README.md):
principles, the full card library by role, and every deck's plan and win lines.

- Refresh or add a builder: call `moxfield_import_user` (or rerun it later to pick up changes; hand-written notes are kept),
  then add principles/notes and run `python scripts/build_library_docs.py` to regenerate the markdown.
- Keep the library outside the package with `MTG_MCP_LIBRARY_DIR=/path/to/library`.
- Prices in the library are snapshots for the exact printings listed. Re-check with `price_decklist`.

## Deckbuilding template

Claude builds and tunes Commander decks against The Command Zone's deckbuilding template:

| Category | Default | What counts |
|---|---|---|
| Lands | 38 | Land cards |
| Ramp | 10 | Mana rocks and dorks, land fetch, Treasure, extra land drops |
| Card advantage | 12 | Draw and other sources of extra cards |
| Targeted disruption | 12 | Spot removal, counterspells, bounce, edicts |
| Mass disruption | 6 | Board wipes |
| Plan | 30 | Cards for the deck's own strategy |

The targets add up to 108 for 99 slots, so about 9 cards should fill two roles.

To change the numbers, just tell Claude, for example "use 36 lands and 12 ramp". It passes them as `template`, e.g. `{"lands": 36, "ramp": 12}`, to `deckbuilding_template` and `analyze_deck`. The `template` section of `analyze_deck` shows target, actual count and the cards in each category. A card with none of the other roles counts as a plan card.

## Install

Requires Python 3.10+.

```bash
cd mtg-deckbuilder-mcp
pip install -e .          # or: uv pip install -e .
mtg-mcp --help
```

### Claude Desktop

Settings → Developer → Edit Config, then add:

```json
{
  "mcpServers": {
    "mtg-deckbuilder": {
      "command": "mtg-mcp"
    }
  }
}
```

If `mtg-mcp` isn't on the PATH Claude Desktop sees, use the full path (`which mtg-mcp`), or with uv:

```json
"mtg-deckbuilder": {
  "command": "uv",
  "args": ["--directory", "/absolute/path/to/mtg-deckbuilder-mcp", "run", "mtg-mcp"]
}
```

Restart Claude Desktop fully.

### Claude Code

```bash
claude mcp add mtg-deckbuilder -- mtg-mcp
```

### Cursor

`.cursor/mcp.json` runs `${workspaceFolder}/.venv/bin/mtg-mcp`, so create the venv in the repo root once:

```bash
python3 -m venv .venv && .venv/bin/pip install -e .
```

### HTTP (for hosting later)

```bash
mtg-mcp --http --host 0.0.0.0 --port 8000   # serves streamable HTTP at /mcp
```

### Docker

The image runs the same `mtg-mcp` command. No extra args means stdio. Pass the HTTP flags to listen on a port.

```bash
docker build -t mtg-mcp .
docker run --rm mtg-mcp --help
```

Claude Desktop, without a local Python install. `-i` keeps stdin open so the client can talk:

```json
"mtg-deckbuilder": {
  "command": "docker",
  "args": ["run", "-i", "--rm", "mtg-mcp"]
}
```

HTTP, endpoint `http://localhost:8000/mcp`:

```bash
docker run --rm -p 8000:8000 mtg-mcp --http --host 0.0.0.0 --port 8000
```

## Try it

- "Analyze this deck:" + paste a Moxfield export
- "What combos am I one card away from?"
- "Give me 10 EDHREC high-synergy cards for my Atraxa deck under $5 that I'm not already running."
- "Find the five most viewed Archidekt decks for Atraxa in bracket 3 and tell me which cards most of them run that I don't."
- "Find green ramp creatures under $1 legal in Commander."
- "How does Rhystic Study interact with a player who has no untapped mana?"

## Tests

Offline (no network needed; all APIs are faked):

```bash
python -m unittest discover -s tests -v
```

## Notes and limits

- **Scryfall** is used as intended: User-Agent + Accept headers, ~100 ms between requests, batched `/cards/collection` lookups (75 cards per request), and caching. Prices are Scryfall's daily USD prices for the printing it returns (not always the cheapest; use `get_card_printings` for that).
- **EDHREC has no official API.** This reads the JSON its own website loads, slowly and with a 24 h cache. It may break if EDHREC changes those pages. Ask EDHREC before building a public product on it.
- **Archidekt has no documented public API either.** This uses the JSON its website loads (deck search and deck pages), at most one request per second with a 6 h cache. Only public decks are visible. `archidekt_popular_cards` makes one request per sampled deck, so 15 decks takes about 15 seconds.
- **Moxfield has no public API**, so decks come in by paste/export rather than URL.
- **Role tagging** is a regex heuristic over oracle text: good for spotting gaps, not perfect.
- Wizards' Fan Content Policy and Scryfall's terms: keep anything built on this free to use, and don't imply endorsement.

## Layout

```
src/mtg_mcp/
  server.py     MCP tools + entry point
  http.py       rate-limited, cached HTTP client
  scryfall.py   Scryfall API
  decklist.py   decklist parser
  analysis.py   deck analysis + role heuristics
  spellbook.py  Commander Spellbook
  edhrec.py     EDHREC (unofficial)
  archidekt.py  Archidekt deck search and deck lists (unofficial)
  library.py    reference library loader and queries
  moxfield.py   Moxfield user importer (unofficial)
  data/library/ reference library sources (decks, cards, principles, notes)
scripts/build_library_docs.py   regenerate docs/library/ markdown
docs/library/   readable principles, card library and deck notes
tests/          offline tests with faked APIs
```
