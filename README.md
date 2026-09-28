# mtg-deckbuilder-mcp

[![tests](https://github.com/Harshal12355/MTG-Deck-Builder-MCP/actions/workflows/tests.yml/badge.svg)](https://github.com/Harshal12355/MTG-Deck-Builder-MCP/actions/workflows/tests.yml)

An MCP server that lets Claude (or any MCP client) help build and tune Magic: The Gathering decks with real data instead of memory:

- **Scryfall**: card search with full Scryfall syntax, card lookup, rulings, printings, prices
- **Decklists**: paste a list from Moxfield, Arena, Archidekt, MTGO or plain text
- **Deck analysis**: legality, mana curve, colour pips vs land sources, card roles (ramp / draw / removal / wipes / tutors…), gaps vs a typical Commander template, Game Changers, price
- **Commander Spellbook**: combos already in your deck, and combos one card away
- **EDHREC**: high-synergy and top cards for a commander, by theme or budget, skipping cards you already run

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
| `find_combos` | Combos in the deck / one card away (Commander Spellbook) |
| `search_combos` | Search Commander Spellbook, e.g. `card:"Thassa's Oracle"` |
| `edhrec_recommendations` | EDHREC suggestions for a commander; pass `decklist` to get only *new* cards |
| `edhrec_card` | EDHREC data for a single card |

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

### HTTP (for hosting later)

```bash
mtg-mcp --http --host 0.0.0.0 --port 8000   # serves streamable HTTP at /mcp
```

## Try it

- "Analyze this deck:" + paste a Moxfield export
- "What combos am I one card away from?"
- "Give me 10 EDHREC high-synergy cards for my Atraxa deck under $5 that I'm not already running."
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
tests/          offline tests with faked APIs
```
